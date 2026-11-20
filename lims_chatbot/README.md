# 🔬 «O'zbek ko'mir LIMS» — AI yordamchi (Text-to-SQL, LangGraph)

Bitta chat orqali **laboratoriya bazasidan ma'lumot oluvchi** AI yordamchi. Savol
o'zbekcha yoziladi, yordamchi xavfsiz `SELECT` tuzadi, read-only bazada bajaradi
va javobni jadval bilan qaytaradi. Faqat LIMS mavzusida javob beradi; begona va
xavfli so'rovlarni rad etadi. Davomli savollarni ham tushunadi («ulardan qaysilari...»).

## Java backend va React frontend

- [Java backend: API, autentifikatsiya va SSE proksi](docs/JAVA_BACKEND.md)
- [React frontend: streaming parser va chat komponenti](docs/REACT_FRONTEND.md)

## Joriy ko'mir bazasi — 9-noyabr 2026

`schema.json` va `ddl.sql` yangi `mycoallimsdb` bazasidan yangilandi: 137 ta
jadval/view, 1 732 ustun va 109 ta FK. Ulanish `.env` dagi `DB_*` orqali olinadi.

- `domain_profile.py` joriy sxemadan `coal`, eski `tnb` yoki umumiy profilni
  tanlaydi. `coal_domain.py` ko'mir namligi/kulliligi, standartlar, vagon va
  avtotransport dalolatnomalari, uchastkalar hamda radiatsiya jadvallarini izohlaydi.
- Ko'mir natijalari `laboratory_results` da. TNB partiyasi tahlil holati
  `"analysisStatus"` da; eski `analysis_status` yoki `sampling_point_code` ustunlari
  yangi sxemaga qo'shilmaydi. Eski bazadagi taxminiy FK lar coal profiliga ko'chirilmaydi.
- `coal_sql_catalog.py` 10 ta ko'mir so'rovini beradi. Umumiy katalogdan faqat
  joriy sxemaga mos misollar tanlanadi; tez javob yo'li ham shu tekshiruvdan o'tadi.
- Baza sessiyasining vaqt zonasi `Asia/Tashkent`. `/api/schema` javobida faol
  profil ko'rsatiladi. O'qish huquqi yo'q bo'lsa, chatbot ruxsat xabarini qaytaradi.
- Administrator ruxsat berishi kerak bo'lsa, `schema/grant_mycoal_read_access.sql`
  mavjud jadvallar uchun tayyorlangan. Ilova bu faylni avtomatik bajarmaydi.

Yangi savol namunalari:

```text
Bugun nechta ko'mir laboratoriya natijasi qayd etilgan?
Oxirgi 20 ta ko'mir laboratoriya natijasi
Uchastkalar bo'yicha ko'mir laboratoriya natijalari soni
Shu oy vagon hisob dalolatnomalari soni va jami vazni
Ko'mir markalari bo'yicha standartlar
Ish jurnalida nechta alohida ekskavator bor?
```

«Jami ekskavatorlar nechta?» va ish jurnalidagi ekskavatorlar haqidagi savollar
`COUNT(DISTINCT excavator_number)` orqali sanaladi:
sana va smenalardagi takroriy yozuvlar bir marta hisoblanadi. Javob soni bazadan
olinadi va javobda ish jurnali sanalgani ko'rsatiladi. Faqat ma'lumotnomadagi son
aniq so'ralsa, `excavators` jadvali sanaladi.

`python -m lims_chatbot.tools.evaluate` faol profilga mos baholash savollarini
tanlaydi (`coal_eval_set.py` yoki eski `eval_set.py`). To'liq baholash uchun baza
va `.env` dagi LLM xizmati ishlashi kerak. Quyidagi eski TNB misollari ushbu
loyihaning oldingi profiliga tegishli.

## Arxitektura

```
POST /api/chat {question, session_id}
      │
      ▼
 screen (security.py) ── xavfli ──► blocked (LLM ga bormaydi)
      │
      ▼
 classify — BITTA LLM chaqiruvi: yo'nalish + kerakli jadvallar (ruxsatli jadval/view katalogidan)
      ├──► chitchat / refuse
      ▼
 database (sql_service.py)
   1. TEZ YO'L: savol tekshirilgan shablonga aniq mos kelsa — SQL LLM'siz (sql_catalog.py)
   2. prompt = qoidalar + domen bilimi + tanlangan jadvallar DDL i (FK qo'shnilari bilan,
               barqaror tartibda — vLLM prefiks keshi) + 3 ta o'xshash tekshirilgan misol
               + suhbat tarixi
   3. SQL → sql_guard (faqat o'qish) → sql_validator (jadval/ustun/qiymat sxemada bormi)
   4. xato bo'lsa — model savolni, o'z SQL ini va ANIQ xatoni ko'rib qayta yozadi
      (bir xil xato takrorlansa to'xtaydi)
   5. natija LIMIT+1 bilan; kesilsa jami son alohida hisoblanadi
   6. javob (answer_format.py) = LLM xulosasi + natija ro'yxati:
      xulosa savolga to'g'ridan-to'g'ri javob beradi (1-3 gap); undagi sonli qiymatlarni kod chiqaradi. Scalar natija LLM tomonidan qayta yozilmaydi;
      ko'p satrli natijada LLM faqat miqdorsiz izoh yozadi.
      Ro'yxatni (20 tagacha satr) kod yozadi — nom va sonlar bazadagidek.
```

### Javob matni

Javob — toza oddiy matn: markdown, emoji va qo'shtirnoqlar yo'q (LLM yozganidan ham
tozalanadi). Sanalar `18.09.2026`, vaqt `10:23`. Masalan:

```
Shu oyda 21 ta sexda jami 156 ta tahlil o'tkazilgan, ulardan 22 tasida chetlanish aniqlangan.

1. 912-sex labaratoriyasi: tahlillar soni 33, chetlanishlar soni 11
2. 916-sex labaratoriyasi: tahlillar soni 27, chetlanishlar soni 2
...
Jami: tahlillar soni 156, chetlanishlar soni 22
```

«Jami» ni kod hisoblaydi (LLM ga qo'shish taqiqlangan): faqat oddiy `GROUP BY` so'rovidagi
`count(*)` / `sum(...)` ustunlari uchun, LIMIT/HAVING bo'lmasa va natija to'liq bo'lsa.

Ma'lumot olinmasa foydalanuvchiga texnik tafsilotsiz javob beriladi («Savolni aniqroq
yozib ko'ring...»); aniq sabab `error` maydonida va suhbat xotirasida qoladi.

### Javob tili — `lang`

So'rovdagi `lang`: `uz` (standart), `ru`, `en`. Savol istalgan tilda yozilishi mumkin,
javob — `lang` tilida:

| Qism | Qanday |
|------|--------|
| Xulosa va suhbat (LLM) | promptlar o'zbekcha, oxirida javob tili ko'rsatmasi (`prompts.ANSWER_LANGUAGE`) — o'zgarmas qism vLLM keshida qoladi |
| Ro'yxat sarlavhalari | SQL ustun taxalluslari shu tilda yoziladi (`AS количество_анализов`, `AS analysis_count`) |
| Tayyor xabarlar (rad, xato, bloklash) | `prompts.MESSAGES` — har biri uch tilda |
| Kod yozadigan qism («jami 900 ta», «ko'rsatilmagan», «ha/yo'q») | `answer_format.TEXTS` |

Bazadagi nomlar (sex, nazorat nuqtasi, mahsulot) tarjima qilinmaydi — bazadagidek chiqadi.
Katalog tez yo'li (`sql_catalog.find_match`) faqat `uz` da ishlaydi (shablon taxalluslari o'zbekcha).

```powershell
python -m lims_chatbot.tools.evaluate --lang ru   # javob tili o'zgarganda SQL aniqligini tekshirish
```

## Aniqlik manbalari (eng muhimidan)

| Nima | Qayerda | Nima beradi |
|------|---------|-------------|
| **Baza sxemasi** | `schema/schema.json`, `schema/ddl.sql` | Ustunlar, PK/FK, **CHECK qiymatlari**, **bazada haqiqatda uchraydigan qiymatlar** (sonlari bilan), `status_dictionary` kodlari, doim-NULL ustunlar, sana oraliqlari |
| **Domen bilimi** | `app/domain.py` | Jadval izohlari, FK e'lon qilinmagan **mantiqiy bog'lanishlar**, umumiy qoidalar (TNB vs umumiy modul, lotin/kirill qidiruv, arxiv), lug'at |
| **Tekshirilgan misollar** | `app/sql_catalog.py` | 30 ta bazada bajarilgan savol→SQL; promptga namuna + tez yo'l |
| **SQL tekshiruvchi** | `app/sql_validator.py` | Mavjud bo'lmagan jadval/ustun va bazada uchramaydigan qiymat (`status = 'approved'`) bazaga yetmasdan ushlanadi |
| **Baholash** | `tools/evaluate.py`, `tools/eval_set.py` | Aniqlik foizda o'lchanadi |

### Sxemani yangilash (baza o'zgarganda)

```powershell
# loyiha ildizidan, baza tarmog'ida (VPN)
python -m lims_chatbot.tools.generate_ddl                # bazadan (faqat o'qish): schema.json + ddl.sql
python -m lims_chatbot.tools.generate_ddl --render-only  # bazasiz: domain.py izohlari o'zgarganda
```

`.env` dagi `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` boshqa bazaga
o'zgartirilsa, xizmatni qayta ishga tushiring va yuqoridagi generatorni yangi
ulanish bilan bajaring. Oddiy ish rejimida boshqa bazaga tegishli snapshot
ishlatilmaydi: jonli sxema talab qilinadi; ulanish ishlamasa sxema mavjud emas
deb qaytariladi. Eski bazadagi namuna qiymatlar yangi sxemaga ko'chirilmaydi.
SQL promptiga faqat joriy sxema tekshiruvidan o'tgan katalog misollari qo'shiladi.
`SCHEMA_REFRESH_SECONDS=0` — berilgan snapshotga ishonadigan test/offline rejim;
yangi bazaga o'tishda uni yoqmang.

Fayllar repoga kiradi (Docker image ham ulardan foydalanadi). Shaxsiy va erkin
matnli ustunlar qiymatlari (ism, email, izoh, raqamlar) faylga YOZILMAYDI.

### Aniqlikni o'lchash

```powershell
python -m lims_chatbot.tools.evaluate                 # to'liq quvur: haqiqiy LLM + baza
python -m lims_chatbot.tools.evaluate --only 3,7
```

`eval_set.py` ga real foydalanuvchilar bergan savollarni qo'shib boring — har
o'zgarishdan keyin natija raqamda ko'rinadi.

## 🔒 Bazani himoya qilish — 6 qatlam

| # | Qatlam | Nima qiladi |
|---|--------|-------------|
| 1 | **Kirish filtri** (`security.py`) | Buzg'unchi niyat, prompt-injection, parol ovlashni **LLM ga bormasdan** bloklaydi |
| 2 | **Read-only DB foydalanuvchi** | Yozish huquqi yo'q (167 jadvalda faqat SELECT — tekshirilgan) |
| 3 | **Read-only sessiya** | `default_transaction_read_only=on` + `statement_timeout` |
| 4 | **SQL qo'riqchisi** (`sql_guard.py`) | AST: faqat 1 ta SELECT; yozuv/DDL, `SELECT ... INTO`, `FOR UPDATE`, xavfli funksiyalar, `pg_authid`, maxfiy ustunlar — rad. So'rov AST'dan qayta render qilinadi |
| 5 | **Natija himoyasi** | Majburiy `LIMIT`, maxfiy ustun va ichki JSON kalitlari niqobi (`***`), massiv/chuqurlik/hajm chegaralari |
| 6 | **Login/parol** (HTTP Basic) | Barcha endpointlar `.env` dagi `API_USERNAME` / `API_PASSWORD` bilan yopiq. Sozlanmagan bo'lsa hamma so'rov rad etiladi |

## Endpointlar (Swagger: `/docs`)

Foydalanish faqat Swagger orqali: `http://<server>:10405/docs` → **Authorize** → login/parol →
`POST /api/chat` → **Try it out**. `/` manzili `/docs` ga yo'naltiradi.

| Metod | Yo'l | Vazifa |
|-------|------|--------|
| POST | `/api/chat` | `{"question": "...", "session_id": "...", "lang": "uz"}` → javob, SQL, jadval, `session_id` |
| POST | `/api/chat/stream` | Xuddi shu so'rov → bosqichma-bosqich SSE oqimi (quyida) |
| POST | `/api/chat/page` | `{cursor}` — natijaning keyingi 20 qatori; LLM qayta chaqirilmaydi |
| GET  | `/api/schema` | Sxema manbasi, yaratilgan vaqti, jadvallar soni |
| GET  | `/healthz` | Holat (LLM modeli, baza ulanishi, schema.json, suhbat xotirasi) |

## Oqim — `POST /api/chat/stream` (`streaming.py`)

Javob matni LLM yozishi bilan bo'laklab keladi (`text/event-stream`) — foydalanuvchi
to'liq javobni kutib qolmaydi. Ichki jarayon (jadvallar, SQL, urinishlar) oqimga
chiqmaydi. So'rov va yakuniy natija `/api/chat` bilan bir xil.

```
event: start    data: {"session_id": "…"}                  ← darhol
event: delta    data: {"text": "Shu oy eng ko'p tahlil "}  ← javob bo'laklari (0..n)
event: delta    data: {"text": "Ammiak sexida…"}
event: result   data: { …/api/chat javobi… }               ← oxirgi; `answer` — yakuniy matn
event: error    data: {"detail": "…"}                      ← faqat kutilmagan xatoda
: ping                                                     ← jim paytda har 10 s
```

* Tokenlab LLM yozadigan qism keladi (natija xulosasi, suhbat); natija ro'yxati xulosadan
  keyin bitta `delta` bo'lib keladi. LLM'siz tuziladigan javoblar (xato, aniqlashtirish,
  bloklangan savol) `delta` siz, darhol `result` da keladi.
* Xulosadagi sonlar oqimda ham tekshiriladi (`graph.NumberGuard`): son to'liq yozilguncha
  ushlab turiladi, natijada yo'q son ekranga CHIQMAYDI — LLM darhol to'xtatiladi va
  `result.answer` da qoidaviy javob keladi. Shuning uchun mijoz `result` kelganda
  ko'rsatilgan matnni `result.answer` bilan almashtirishi kerak.
* Mijoz uzilsa (yoki "To'xtatish") graf bekor qilinadi — LLM bekor ishlamaydi; savol
  (yozilgan qismi bilan) xotiraga `route = cancelled` bilan yoziladi.
* Baza ulanishi xatosida SQL qayta yozdirilmaydi — darhol «Bazaga ulanib bo'lmadi» javobi.
* Brauzerda `EventSource` POST va login yubora olmaydi — `fetch` + `ReadableStream` ishlating.
  Proksi (nginx) orqasida `X-Accel-Buffering: no` allaqachon yuboriladi; frontend boshqa
  manzilda bo'lsa `CORS_ALLOW_ORIGINS` uni (yoki `*`) o'z ichiga olishi kerak.

Frontend uchun minimal o'quvchi:

```js
const res = await fetch(`${API}/api/chat/stream`, {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: "Basic " + btoa(`${login}:${parol}`) },
  body: JSON.stringify({ question, session_id, lang }),   // lang: "uz" | "ru" | "en"
  signal: controller.signal,                       // controller.abort() — to'xtatish
});
const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
let buf = "", text = "";
for (let r; !(r = await reader.read()).done; ) {
  buf += r.value;
  for (let i; (i = buf.indexOf("\n\n")) >= 0; buf = buf.slice(i + 2)) {
    const block = buf.slice(0, i);
    if (block.startsWith(":")) continue;           // ping
    const event = block.match(/^event: (.*)$/m)?.[1];
    const data = JSON.parse(block.match(/^data: (.*)$/m)[1]);
    if (event === "start") session_id = data.session_id;
    if (event === "delta") show(text += data.text);
    if (event === "result") show(data.answer);    // yakuniy (tekshirilgan) matn + data.rows
    if (event === "error") showError(data.detail);
  }
}
```

## Suhbat xotirasi (`memory.py`)

Har bir savol-javob alohida PostgreSQL bazasiga (`.env` dagi `CHAT_DB_*`, yozish
huquqi bilan) yoziladi — LIMS bazasi read-only bo'lgani uchun u yerga emas.
Jadvallar birinchi murojaatda o'zi yaratiladi (`CHAT_DB_TABLE_PREFIX=lims_chatbot`):

| Jadval | Satr | Asosiy ustunlar |
|--------|------|-----------------|
| `lims_chatbot_sessions` | bitta suhbat | `id` (= session_id), `title` (birinchi savol), `message_count`, `created_at`, `updated_at` |
| `lims_chatbot_messages` | bitta savol-javob | `session_id`, `question`, `answer`, `route`, `sql_query`, `row_count`, `error`, `duration_ms`, `meta` (jsonb), `created_at` |

* Barcha savollar saqlanadi (chitchat, bloklangan, xato bilan tugaganlari ham);
  davomli savol konteksti uchun muvaffaqiyatli SQL va kutilayotgan aniqlashtiruvchi savollardan oxirgi 4 tasi o'qiladi.
* Natija satrlari saqlanmaydi (katta va maxfiy bo'lishi mumkin) — SQL yetarli.
* `session_id` yuborilmasa yangisi yaratiladi va javobda qaytadi.
* Xotira bazasi ishlamasa chat to'xtamaydi (tarix bo'sh, xato logda);
  holatini `/healthz` → `memory_ok` ko'rsatadi.
* `CHAT_DB_HOST` bo'sh bo'lsa xotira jarayon ichida (qayta ishga tushsa yo'qoladi).

Foydali so'rovlar:

```sql
-- Oxirgi savollar
SELECT created_at, session_id, route, question FROM lims_chatbot_messages ORDER BY id DESC LIMIT 50;
-- Xato bilan tugagan savollar (eval_set.py ga nomzodlar)
SELECT question, error FROM lims_chatbot_messages WHERE error IS NOT NULL ORDER BY id DESC;
```

## Testlar

```powershell
pytest      # loyiha ildizidan; baza ulangan bo'lsa katalog SQL lari bazada ham bajariladi

# suhbat xotirasini haqiqiy PostgreSQL da ham tekshirish (vaqtinchalik test jadvallari yaratib o'chiriladi):
$env:TEST_CHAT_DB_URL = "postgresql://user:parol@localhost:5432/db"; pytest lims_chatbot/tests/test_memory.py
```

Qamrov: SQL qo'riqchisi va tekshiruvchisi, kirish filtri, sxema tanlash, DDL
generatori, katalog va domen izohlarining bazaga mosligi, Text-to-SQL qayta
urinish mantig'i, javobdagi sonlar nazorati, API (login, suhbat xotirasi), xotira bazasi.

## Loyiha tuzilishi

```
app/
  api.py             FastAPI router (chat + schema + health), main.py ga ulanadi
  auth.py            HTTP Basic avtorizatsiya (main.py da butun ilovaga ulanadi)
  graph.py           LangGraph: screen → classify (+ jadval tanlash) → database / chitchat / refuse
  sql_service.py     Text-to-SQL: tez yo'l, misollar, tekshiruv, qayta urinish, kesish
  sql_validator.py   SQL ni sxema bo'yicha tekshirish (jadval/ustun/qiymat)
  sql_catalog.py     Tekshirilgan savol→SQL katalogi
  sql_guard.py       SQL AST himoyasi (faqat o'qish)
  schema_catalog.py  schema.json modeli + DDL chizish
  schema_provider.py Jadval katalogi, DDL to'plami (FK qo'shnilari bilan), leksik zaxira
  domain.py          Domen bilimi: izohlar, mantiqiy FK, qoidalar, lug'at
  memory.py          Suhbat xotirasi: PostgreSQL (CHAT_DB_*) yoki jarayon xotirasi
  streaming.py       Javob tokenlarini oqimga uzatish (delta/listen) — /api/chat/stream uchun
  answer_format.py   Javob matni: qiymatlar ko'rinishi, natija ro'yxati, qoidaviy javob, belgilarni tozalash
  security.py        Kirish xavfsizlik filtri
  db_client.py       PostgreSQL read-only + JSON konvertatsiya + niqoblash
  llm.py             vLLM (chat) klienti
  prompts.py         Promptlar
  config.py          .env sozlamalari
  schemas.py         API modellari
schema/                 schema.json + ddl.sql (generate_ddl yaratadi)
tools/generate_ddl.py   sxemani bazadan yaratish (read-only)
tools/evaluate.py       aniqlikni o'lchash; eval_set.py — savollar
tests/                  testlar```

## Eslatma

Baza LAN'da (`192.168.1.7`, tashqaridan VPN orqali). `database` yo'nalishi baza
ulanganda ishlaydi; `chitchat`/`refuse`/`blocked` mustaqil ishlaydi.
Suhbat xotirasi bazasi ham LAN'da (`192.168.1.27`) — ulanmasa chat ishlayveradi, faqat tarix saqlanmaydi.


## Xavfsizlik va sxema yangilanishi — 5-noyabr 2026

- Sxema yangilanganda 565 ta ruxsatli jadval va 9 ta view (jami 574 ta obyekt,
  7 016 ustun) olindi. `flyway_schema_history` ataylab chiqariladi.
  Ruxsatsiz jadvallar uchun huquq avtomatik berilmaydi.
- `SchemaProvider` snapshotni yuklagach jonli metadata bilan tekshiradi va
  `SCHEMA_REFRESH_SECONDS` (standart 600) oralig'ida yangilaydi. Jonli metadata
  jadval, ustun, CHECK va huquqlar uchun asosiy manba. Eski namuna qiymatlar
  majburiy enum hisoblanmaydi. Test/offline rejim uchun `SCHEMA_REFRESH_SECONDS=0`.
- Jonli introspeksiya faqat o'qish huquqi bor obyektlarning ustun va cheklovlarini
  oladi; izohlar tizim katalogiga JOIN orqali yuklanadi. Metadata uchun vaqt
  chegarasi kamida 60 soniya; foydalanuvchi SQLlari `STATEMENT_TIMEOUT_MS`
  chegarasida qoladi. Katta sxema dastlab yuklanishi tayyorlik tekshiruvini
  sekinlashtirishi mumkin.
- Router savolga yaqin jadvallarning izohini, qolgan ruxsatli jadvallarning esa
  qisqa nomlarini oladi. Har bir katalog obyekti tanlash uchun mavjud.
- SQL DB adapterida ham tekshiriladi: faqat bitta read-only so'rov, aniq ustunlar,
  tekshirilgan builtin funksiyalar, ruxsatli sxema. SELECT *, butun qatorni
  serializatsiya qilish, pozitsiyali ustun aliaslari, maxsus operator/cast va
  tekshirilmagan funksiyalar rad etiladi. JSON transformatsiyasi CTE/ichki
  so'rov orqali ham niqoblashni chetlab o'ta olmaydi.
- JSON natijalari rekursiv niqoblanadi. Ichki massiv/lug'at 100 element, chuqurlik
  8, yakuniy natija taxminan 1 MB bilan cheklangan; ortiqcha natija ochiq xato
  bilan qayta toraytiriladi. Oddiy uzun matnlar 400 belgida kesiladi.
- `tnb_analysis.inputs_json/sections_json` va tasdiqlangan kiruvchi nazorat JSON
  OID ustunlarini alohida tanlash mumkin. Adapter PostgreSQL qaytargan haqiqiy
  jadval/ustun kelib chiqishini tekshiradi; faqat shu ustunlarga tegishli JSONni
  100 KB chegarada o'qib, maxfiy kalitlarni niqoblaydi. Modelga `lo_get` chaqirish
  ruxsati berilmaydi. HTML, imzo va boshqa OID ustunlar bu yo'lga kirmaydi.
- `/healthz` haqiqiy qisqa LLM completion, DB, xotira va sxema holatini tekshiradi;
  dependency ishlamasa HTTP 503 va `status=degraded` qaytadi. LLM readiness uchun
  `LLM_HEALTH_TIMEOUT` standarti 10 soniya; SDK retry soni `LLM_MAX_RETRIES=1`.
- API texnik xato sababini foydalanuvchiga oshkor qilmaydi: `error=request_failed`;
  tekshirish uchun tafsilot server logi va ichki suhbat yozuvida qoladi.

### Katta ro'yxatning keyingi sahifasi

Chat javobida natija kesilgan bo'lsa, `next_cursor` keladi. Uni o'sha autentifikatsiya
bilan `POST /api/chat/page` ga `{"cursor":"..."}` ko'rinishida yuboring. Javob:
`columns`, `rows`, `row_count`, `next_cursor`. Cursor SQLni mijozdan qabul qilmaydi,
faqat serverda saqlangan so'rovga tegishli; 15 daqiqada eskiradi. Har sahifada joriy
sxema va SQL himoyalari qayta tekshiriladi. Server qayta ishga tushsa cursor yo'qoladi.
Bir nechta worker/replika ishlatilsa birinchi va keyingi sahifa bir workerga borishi
kerak (sticky routing). Baza sahifalar orasida o'zgarsa natija ham o'zgarishi mumkin;
bu uzoq yashovchi tranzaksiya yoki muzlatilgan eksport emas.

### Alohida foydalanuvchilar

Mavjud `API_USERNAME`/`API_PASSWORD` ishlaydi. Bir nechta alohida account kerak bo'lsa,
`API_ACCOUNTS` JSON lug'atini muhit orqali bering, masalan username → password.
Suhbat tarixi autentifikatsiyadan o'tgan account va `session_id` bo'yicha ajratiladi;
boshqa account bir xil `session_id` yoki cursor bilan tarix/natijaga kira olmaydi.
Bitta loginni bo'lishadigan odamlar bitta principal hisoblanadi. Bu accountlar bir
xil read-only LIMS DB huquqlaridan foydalanadi; laboratoriya/rol kesimida huquqlar
uchun alohida DB/view siyosati kerak.

### Tekshirish

`pytest` oddiy testlarda jonli LLMni chaqirmaydi va ishlab turgan chat bazasiga yozmaydi.
Katalog SQLlari LIMSga ulanish mavjud bo'lsa haqiqiy read-only bazada ham tekshiriladi.
`python -m lims_chatbot.tools.evaluate` esa haqiqiy LLM + LIMS orqali 32 savolni
nazorat SQLlariga solishtiradi, shu jumladan yangi jadvallar va davomli savollar.
Kesilgan natijada ko'rsatilgan qatorlar hamda jami son tekshiriladi; ko'rsatilmagan
qatorlarning barcha qiymatlari shu tekshiruv bilan isbotlangan hisoblanmaydi.

OID JSON uchun PostgreSQL Large Object SELECT huquqi jadval SELECT huquqidan
alohida. Yetishmasa bot ruxsat xabarini qaytaradi va so'rovni boshqa ma'lumotga
almashtirmaydi. DBA tekshirishi uchun [grant_json_objects.sql](schema/grant_json_objects.sql)
faqat tasdiqlangan biznes JSON ustunlari ko'rsatgan obyektlarga SELECT beradi.
Ilova bu skriptni avtomatik bajarmaydi; yangi yaratiladigan obyektlar uchun ham
o'z yaratilish jarayonida tegishli huquq berilishi kerak.
