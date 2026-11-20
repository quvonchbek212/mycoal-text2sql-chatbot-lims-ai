# LIMS chatbot: React frontend va streaming

Backend integratsiyasi: [JAVA_BACKEND.md](JAVA_BACKEND.md).
Quyidagi namuna React ilovasiga qo'shiladigan JavaScript/JSX kodidir.

## Frontend ulanishi

Frontend **Java backend** dagi `POST /api/lims/chat/stream` ga murojaat qiladi.
Java Python chatbotga HTTP Basic bilan ulanadi. React mavjud ilovadagi
foydalanuvchi autentifikatsiyasini ishlatadi; chatbot login/paroli frontend
`.env`, `VITE_*`, `REACT_APP_*` yoki JavaScript bundle'ga qo'yilmaydi.

Bu endpoint `POST` va JSON tana qabul qiladi. Brauzerning oddiy
`EventSource` API'si o'rniga `fetch` + `ReadableStream` ishlatiladi.

```json
{
  "question": "Jami ekskavatorlar nechta?",
  "session_id": null,
  "lang": "uz"
}
```

`question`: 1–3000 belgi. `lang`: `uz`, `ru`, `en`. Birinchi so'rovda
`session_id` yuborilmaydi yoki `null`; `start.session_id` keyingi savollarda
qayta yuboriladi. Yangi suhbat ochilganda session tozalanadi. Brauzerni
yangilagandan keyin ham suhbatni davom ettirish kerak bo'lsa, sessionni
foydalanuvchi hisobiga bog'lab saqlash alohida qo'shiladi.

| SSE hodisa | Frontend amali |
|---|---|
| `start` → `{session_id}` | Sessionni saqlash |
| `delta` → `{text}` | Vaqtinchalik javob oxiriga qo'shish |
| `result` → to'liq javob | `answer` bilan matnni almashtirish, jadvalni ko'rsatish |
| `error` → `{detail}` | Xato ko'rsatish |
| `: ping` | Izoh, UI'da ko'rsatilmaydi |

`delta` kelmasligi ham mumkin. Bir tarmoq chunk'i bir nechta SSE hodisasini
olib kelishi yoki hodisaning yarmi bo'lishi mumkin. UTF-8 belgisi ham
chunk'lar orasida bo'linadi. Shu sabab chunk'ni bevosita `JSON.parse`
qilmang. Parser inkremental dekoder va hodisa chegaralarini ishlatishi kerak.

## Oqimni o'qish: `src/limsChatStream.js`

```js
export async function streamLimsChat({
  question,
  sessionId,
  lang = "uz",
  signal,
  authHeaders = {},
  onEvent,
}) {
  const response = await fetch("/api/lims/chat/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
      ...authHeaders,
    },
    body: JSON.stringify({ question, session_id: sessionId, lang }),
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : null;
    throw new Error(detail || `So'rov bajarilmadi (HTTP ${response.status})`);
  }
  if (!response.headers.get("content-type")?.includes("text/event-stream")) {
    throw new Error("Server SSE formatida javob bermadi");
  }
  if (!response.body) throw new Error("Brauzer oqimni o'qiy olmadi");

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let eventName = "message";
  let dataLines = [];
  let completed = false;

  function line(value) {
    if (value === "") {
      if (dataLines.length) {
        const payload = JSON.parse(dataLines.join("\n"));
        if (eventName === "error") {
          throw new Error(payload.detail || "Javob oqimida xato yuz berdi");
        }
        onEvent(eventName, payload);
        if (eventName === "result") completed = true;
      }
      eventName = "message";
      dataLines = [];
      return;
    }
    if (value.startsWith(":")) return;
    const colon = value.indexOf(":");
    const field = colon === -1 ? value : value.slice(0, colon);
    let content = colon === -1 ? "" : value.slice(colon + 1);
    if (content.startsWith(" ")) content = content.slice(1);
    if (field === "event") eventName = content;
    if (field === "data") dataLines.push(content);
  }

  function feed(text, eof = false) {
    buffer += text;
    while (!completed) {
      const match = /\r\n|\r|\n/.exec(buffer);
      if (!match) break;
      // CRLF ikki tarmoq chunk'iga bo'lingan bo'lishi mumkin.
      if (!eof && match[0] === "\r" && match.index === buffer.length - 1) break;
      const value = buffer.slice(0, match.index);
      buffer = buffer.slice(match.index + match[0].length);
      line(value);
    }
  }

  try {
    while (!completed) {
      const { value, done } = await reader.read();
      if (done) {
        feed(decoder.decode(), true);
        break;
      }
      feed(decoder.decode(value, { stream: true }));
    }
    if (!completed) {
      throw new Error("Javob tugamasdan aloqa uzildi. Savolni qayta yuboring.");
    }
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
```

Parser LF, CRLF va CR satr ajratgichlarini, ko'p qatorli `data` maydonini,
izoh/heartbeat va bo'lingan UTF-8 belgilarini qo'llaydi. SSE hodisasi bo'sh
satr bilan tugashi kerak. `result` kelgach transport resurslari yopiladi.
POST avtomatik takrorlanmaydi: qayta yuborish suhbatda takroriy savol yozishi
mumkin. Foydalanuvchi xatodan keyin qayta yuborishni o'zi tanlaydi.

## React komponenti: `src/LimsChat.jsx`

```jsx
import { useEffect, useRef, useState } from "react";
import { streamLimsChat } from "./limsChatStream";

function cell(value) {
  if (value == null) return "—";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

export default function LimsChat({ authHeaders = {} }) {
  const [question, setQuestion] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const active = useRef(null);

  useEffect(() => () => active.current?.abort(), []);

  function patch(id, update) {
    setMessages(items => items.map(item =>
      item.id === id ? { ...item, ...update(item) } : item));
  }

  async function send(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text || text.length > 3000 || active.current) return;

    const controller = new AbortController();
    active.current = controller;
    const answerId = crypto.randomUUID();
    setMessages(items => [...items,
      { id: crypto.randomUUID(), role: "user", text },
      { id: answerId, role: "assistant", text: "", status: "loading" },
    ]);
    setQuestion("");
    setLoading(true);

    try {
      await streamLimsChat({
        question: text,
        sessionId,
        lang: "uz",
        signal: controller.signal,
        authHeaders,
        onEvent: (name, payload) => {
          if (name === "start") setSessionId(payload.session_id);
          if (name === "delta") {
            patch(answerId, item => ({ text: item.text + payload.text }));
          }
          if (name === "result") {
            // Yakuniy matn qo'shilmaydi: oldingi preview o'rniga yoziladi.
            setSessionId(payload.session_id);
            patch(answerId, () => ({
              text: payload.answer || "",
              result: payload,
              status: payload.error ? "error" : "done",
              error: payload.error ? "Javobni tayyorlashda xato yuz berdi." : null,
            }));
          }
        },
      });
    } catch (error) {
      const cancelled = controller.signal.aborted;
      patch(answerId, () => ({
        text: "", // Tugallanmagan preview yakuniy javob sifatida qolmaydi.
        status: cancelled ? "cancelled" : "error",
        error: cancelled ? "Javob to'xtatildi." : error.message,
      }));
    } finally {
      active.current = null;
      setLoading(false);
    }
  }

  function newChat() {
    if (active.current) return;
    setSessionId(null);
    setMessages([]);
    setQuestion("");
  }

  return (
    <section aria-label="LIMS yordamchi">
      <button type="button" onClick={newChat} disabled={loading}>
        Yangi suhbat
      </button>

      <div role="log" aria-live="polite" aria-relevant="additions text">
        {messages.map(message => (
          <article key={message.id}>
            <strong>{message.role === "user" ? "Siz" : "LIMS yordamchi"}</strong>
            <div style={{ whiteSpace: "pre-wrap" }}>
              {message.text || (message.status === "loading" ? "Javob tayyorlanmoqda…" : "")}
            </div>
            {message.error && <p role="alert">{message.error}</p>}

            {!message.result?.error && message.result?.rows?.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead><tr>
                    {message.result.columns.map(column => <th key={column}>{column}</th>)}
                  </tr></thead>
                  <tbody>
                    {message.result.rows.map((row, index) => (
                      <tr key={index}>
                        {message.result.columns.map(column => (
                          <td key={column}>{cell(row[column])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {message.result?.truncated && (
              <p>Natijaning bir qismi ko'rsatildi. Savolni sana yoki uchastka bo'yicha aniqlashtiring.</p>
            )}
          </article>
        ))}
      </div>

      <form onSubmit={send}>
        <label htmlFor="lims-question">Savolingiz</label>
        <textarea id="lims-question" value={question} maxLength={3000}
          onChange={event => setQuestion(event.target.value)} disabled={loading} />
        <button type="submit" disabled={loading || !question.trim()}>Yuborish</button>
        {loading && (
          <button type="button" onClick={() => active.current?.abort()}>To'xtatish</button>
        )}
      </form>
    </section>
  );
}
```

Komponent bitta faol so'rovga ruxsat beradi. Bu bir suhbatga parallel savollar
yuborilib, xotira tartibi chalkashishining oldini oladi. Route nomidan qat'i
nazar, foydalanuvchiga `answer` ko'rsatiladi; masalan rad etilgan yoki
aniqlashtirish talab qilingan savolda jadval bo'lmasligi mumkin.

React matnni odatiy JSX orqali chiqaradi. Markdown renderer qo'shilsa,
xom HTML'ni o'chiring yoki sanitizatsiya qiling. `dangerouslySetInnerHTML`
orqali model matnini to'g'ridan-to'g'ri chiqarmang.

## Autentifikatsiya va local development

Namuna same-origin cookie autentifikatsiyasiga mos. Mavjud loyihada CSRF
token kerak bo'lsa `authHeaders` orqali uzating:

```jsx
<LimsChat authHeaders={{ "X-CSRF-TOKEN": csrfToken }} />
```

Header nomi loyihadagi Spring Security CSRF sozlamasiga mos bo'lsin.
Bearer ishlatilsa ilovaning mavjud access tokenini yuboring:

```jsx
<LimsChat authHeaders={{ Authorization: `Bearer ${accessToken}` }} />
```

Bular Java foydalanuvchisining credentiallari. Chatbot xizmatining Basic
login/paroli Java ichida qoladi. Endpointni ommaviy ochib qo'ymang.

Vite ishlatiladigan loyihada development proksi misoli:

```js
// vite.config.js
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/lims": { target: "http://127.0.0.1:8081", changeOrigin: true },
    },
  },
});
```

Frontend boshqa origin'dan Java'ga to'g'ridan-to'g'ri murojaat qilsa URL,
CORS va cookie `credentials: "include"` sozlamalarini moslang. Same-origin
proksi ishlatilsa yuqoridagi `/api/lims/...` nisbiy manzil yetarli.

## Jadval va sahifalash

`result.columns` — ustunlar tartibi, `result.rows` — satrlar,
`row_count` — shu javobdagi satrlar soni. `total_count` `null` bo'lishi
mumkin. Bo'sh natijada `rows=[]` normal holat.

Namuna dastlabki jadval qismini ko'rsatadi. "Yana yuklash" kerak bo'lsa:

1. Java'da foydalanuvchiga bog'langan cursor registri va
   `POST /api/lims/chat/page` proksisi qo'shiladi; backend qo'llanmasiga qarang.
2. `result.next_cursor` mavjud bo'lsa `{"cursor":"..."}` yuboriladi.
3. `PageResponse.rows` oldingi satrlarga qo'shiladi; yangi `next_cursor`
   saqlanadi. `null` kelganda yuklash tugaydi.
4. 404/409 bo'lsa savolni qayta yuborish taklif qilinadi. Cursor muddati
   15 daqiqa, Python restartidan keyin ham yo'qoladi.

Java namunasida `/api/lims/chat/page` hali yo'q; shu endpoint qo'shilmaguncha
frontend undan foydalanmasin. `truncated=true` bo'lishi doim keyingi cursor
borligini anglatmaydi.

## Tekshirish ro'yxati

- Bir so'rovda `start`, nol yoki ko'p `delta`, so'ng `result` ishlaydi.
- `result.answer` oldingi matnni almashtiradi; javob ikki marta takrorlanmaydi.
- `O'zbek`, `ko'mir`, kirillcha va emoji chunk orasida bo'linsa ham buzilmaydi.
- `: ping` ko'rinmaydi, kutish holati `result` gacha saqlanadi.
- Abort tugmasi so'rovni to'xtatadi; keyin yangi savol yuborish mumkin.
- Noto'g'ri HTTP status, SSE `error`, `result.error` va tugallanmagan oqim
  alohida xato holati bo'ladi; bo'sh `rows` esa xato emas.
- Ketma-ket savollar bir xil session bilan, yangi suhbat esa yangi session
  bilan ketadi. Boshqa foydalanuvchining sessioni qabul qilinmaydi.
- Reverse proxy orqali ham matn to'liq javobni kutmasdan bo'laklab keladi.

Kod mavjud React ilovasiga qo'shib build va brauzer integratsiya testidan
o'tkaziladi. Bu repoda React loyiha yo'q; qo'llanma API shartnomasi va
ko'chirib moslashtirish uchun namunalarni beradi.
