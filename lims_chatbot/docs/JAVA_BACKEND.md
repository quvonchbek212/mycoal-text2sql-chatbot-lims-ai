# LIMS chatbot: Java backend integratsiyasi

Ushbu qo'llanma repodagi FastAPI chatbot API'siga mos. React uchun qo'llanma:
[REACT_FRONTEND.md](REACT_FRONTEND.md).

## Ulanish tartibi

```text
React brauzer
  POST /api/lims/chat/stream
        |
        v
Java backend — foydalanuvchi autentifikatsiyasi va SSE proksi
  POST http://lims-chatbot:8080/api/chat/stream
  Authorization: Basic <server sozlamalaridan>
        |
        v
Python chatbot — LLM + LIMS PostgreSQL + suhbat xotirasi
```

Java API login/parolini server sozlamalaridan oladi. React'ga chatbotning
`API_PASSWORD`, baza paroli yoki vLLM kaliti yuborilmaydi. React mavjud
loyihadagi cookie yoki bearer autentifikatsiyasi bilan Java'ga ulanadi.

Quyidagi kod **Java 17+, Spring Boot 3 / WebFlux** loyihasiga qo'shish uchun
namuna. Mavjud Spring MVC ilovasida `ServerHttpResponse` o'rniga servlet
oqim adapteri kerak; ushbu controller WebFlux muhiti uchun yozilgan.
Autentifikatsiyani loyihadagi Spring Security konfiguratsiyasi ta'minlaydi.

## Chatbotning mavjud endpointlari

| Metod | Python endpoint | Vazifasi |
|---|---|---|
| POST | `/api/chat` | To'liq JSON javob |
| POST | `/api/chat/stream` | SSE orqali javob |
| POST | `/api/chat/page` | Jadvalning keyingi sahifasi |
| GET | `/healthz` | Baza, LLM, xotira va sxema holati |
| GET | `/api/schema` | Sxema manbasi, profil va jadval/ustun sonlari |

Besh endpoint ham HTTP Basic talab qiladi. Swagger: `/docs`.
Bu hujjatdagi Java namuna faqat `/api/lims/chat/stream` proksisini yaratadi.
Qolgan Java endpointlar kerak bo'lsa alohida qo'shiladi.

## So'rov va javob shartnomasi

```json
{
  "question": "Jami ekskavatorlar nechta?",
  "session_id": null,
  "lang": "uz"
}
```

| Maydon | Talab |
|---|---|
| `question` | Majburiy, 1–3000 belgi; Java namuna faqat probeldan iborat matnni ham rad etadi |
| `session_id` | Birinchi so'rovda yuborilmasligi yoki `null` bo'lishi mumkin; keyin `start` dagi qiymat yuboriladi |
| `lang` | `uz`, `ru`, `en`; standart `uz` |

Python `session_id` uchun ko'pi bilan 100 belgi va `[A-Za-z0-9_-]+`
formatini qabul qiladi. Quyidagi Java kod bundan torroq, imzolangan format
ishlatadi. React session identifikatorini o'zi yasamaydi.

SSE javobi `Content-Type: text/event-stream` bilan keladi:

```text
event: start
data: {"session_id":"<suhbat-identifikatori>"}

event: delta
data: {"text":"Ish jurnalidagi "}

event: delta
data: {"text":"alohida ekskavatorlar soni: 42"}

event: result
data: {"session_id":"<suhbat-identifikatori>","route":"database","route_reason":"tekshirilgan savol","blocked_category":"","answer":"Ish jurnalidagi alohida ekskavatorlar soni: 42","sql":"SELECT count(DISTINCT excavator_number) AS ish_jurnalidagi_alohida_ekskavatorlar_soni FROM daily_excavator_work","columns":["ish_jurnalidagi_alohida_ekskavatorlar_soni"],"rows":[{"ish_jurnalidagi_alohida_ekskavatorlar_soni":42}],"row_count":1,"total_count":1,"truncated":false,"fast_path":true,"tables":["daily_excavator_work"],"warnings":[],"error":null,"next_cursor":null}

```

Bu protokol misoli; `42` doimiy qiymat emas, natija bazadan olinadi.

| Hodisa | Mazmuni | Mijoz harakati |
|---|---|---|
| `start` | `session_id` | Keyingi savollar uchun saqlash |
| `delta` | `text` | Vaqtinchalik javob oxiriga qo'shish |
| `result` | To'liq `ChatResponse` | Matnni aynan `answer` bilan almashtirish, jadvalni ko'rsatish |
| `error` | `detail` | Oqimdagi xatoni ko'rsatish |
| `: ping` | Taxminan har 10 soniyada SSE izohi | UI'da ko'rsatmaslik |

`delta` nol yoki ko'p marta kelishi mumkin. Natijani `result` belgilaydi;
vaqtinchalik matn keyingi tekshiruvda o'zgarishi mumkin. HTTP 200 ichidagi
`result.error` ham tekshiriladi: `request_failed` bo'lsa so'rov muvaffaqiyatsiz.
`result` yoki `error` kelmasdan oqim tugasa, uni tugallangan javob deb olmang.

## Java sozlamalari

Kerakli starterlar: `spring-boot-starter-webflux`,
`spring-boot-starter-validation` va loyihadagi autentifikatsiya uchun
`spring-boot-starter-security`. Versiyalarni loyihaning Spring Boot BOM'i
boshqarsin. Ushbu proksi modulida `spring-boot-starter-web` qo'shilmaydi.

`application.yml`:

```yaml
server:
  port: 8081

lims:
  chatbot:
    base-url: ${LIMS_CHATBOT_BASE_URL:http://127.0.0.1:8080}
    username: ${LIMS_CHATBOT_USERNAME}
    password: ${LIMS_CHATBOT_PASSWORD}
    session-signing-key: ${LIMS_SESSION_SIGNING_KEY}
```

`LIMS_CHATBOT_USERNAME/PASSWORD` Python xizmatidagi
`API_USERNAME/PASSWORD` bilan mos bo'lishi kerak. `LIMS_SESSION_SIGNING_KEY`
kamida 32 belgili tasodifiy maxfiy qiymat bo'lsin va Java instansiyalarida bir
xil saqlansin. Bu qiymatlarni server environment yoki secret saqlash tizimi
orqali bering. `base-url` chatbot manzili; vLLM'ning `/v1` manzili emas.
Docker ichida `127.0.0.1` o'sha konteynerni bildiradi, shuning uchun Python
xizmatining DNS nomini ishlating, masalan `http://lims-chatbot:8080`.

Quyidagi Java fayllari bir xil `com.example.lims` package ichida bo'lsin.

`LimsChatProperties.java`:

```java
package com.example.lims;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@Validated
@ConfigurationProperties("lims.chatbot")
public record LimsChatProperties(
    @NotBlank String baseUrl,
    @NotBlank String username,
    @NotBlank String password,
    @NotBlank @Size(min = 32) String sessionSigningKey
) {}
```

`LimsChatConfiguration.java`:

```java
package com.example.lims;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import io.netty.channel.ChannelOption;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

@Configuration
@EnableConfigurationProperties(LimsChatProperties.class)
public class LimsChatConfiguration {
    @Bean
    WebClient limsChatClient(LimsChatProperties p) {
        HttpClient transport = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 5000)
            .responseTimeout(Duration.ofSeconds(60));
        return WebClient.builder()
            .baseUrl(p.baseUrl())
            .clientConnector(new ReactorClientHttpConnector(transport))
            .defaultHeaders(h -> h.setBasicAuth(
                p.username(), p.password(), StandardCharsets.UTF_8))
            .build();
    }
}
```

`responseTimeout` bu yerda tarmoqdan o'qishdagi kutish uchun; SSE heartbeat
uzoq davom etadigan javobda ulanishni faol saqlaydi. So'rovning butun hayotiga
10–30 soniyalik limit qo'ymang. `block()`, `collectList()` yoki
`bodyToMono(String.class)` bilan muvaffaqiyatli SSE oqimini yig'mang.

## Suhbatni foydalanuvchiga bog'lash

Python xotirasi `(HTTP Basic foydalanuvchi, session_id)` bo'yicha ajratilgan.
Java barcha mijozlar uchun bitta xizmat loginidan foydalansa, Java'da ham
suhbat egaligi tekshirilishi kerak. Quyidagi imzo boshqa foydalanuvchining
`session_id` qiymatini yuborishni rad etadi. `Principal.getName()` tizimdagi
noyob va barqaror foydalanuvchi identifikatori bo'lishi kerak.

`ChatSessionScope.java`:

```java
package com.example.lims;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.UUID;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

@Component
public class ChatSessionScope {
    private final byte[] key;

    public ChatSessionScope(LimsChatProperties p) {
        key = p.sessionSigningKey().getBytes(StandardCharsets.UTF_8);
    }

    public String resolve(String userId, String supplied) {
        if (supplied == null) {
            String nonce = UUID.randomUUID().toString().replace("-", "");
            return nonce + "_" + sign(userId, nonce);
        }
        if (!supplied.matches("[a-f0-9]{32}_[A-Za-z0-9_-]{43}")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Noto'g'ri session_id");
        }
        String expected = sign(userId, supplied.substring(0, 32));
        boolean valid = MessageDigest.isEqual(
            expected.getBytes(StandardCharsets.US_ASCII),
            supplied.substring(33).getBytes(StandardCharsets.US_ASCII));
        if (!valid) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Bu suhbatga ruxsat yo'q");
        }
        return supplied;
    }

    private String sign(String userId, String nonce) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            byte[] signature = mac.doFinal((userId + "\0" + nonce)
                .getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(signature);
        } catch (java.security.GeneralSecurityException e) {
            throw new IllegalStateException("Session imzosi yaratilmadi", e);
        }
    }
}
```

## SSE proksi controller

`LimsChatController.java`:

```java
package com.example.lims;

import java.nio.charset.StandardCharsets;
import java.security.Principal;
import java.util.Map;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.core.io.buffer.DataBufferUtils;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientRequestException;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/lims")
public class LimsChatController {
    private final WebClient client;
    private final ChatSessionScope sessions;

    public LimsChatController(@Qualifier("limsChatClient") WebClient client,
                              ChatSessionScope sessions) {
        this.client = client;
        this.sessions = sessions;
    }

    public record ChatInput(
        @NotBlank @Size(max = 3000) String question,
        @Size(max = 100) String session_id,
        @Pattern(regexp = "uz|ru|en") String lang
    ) {}

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Mono<Void> stream(@Valid @RequestBody ChatInput input,
                             Principal user, ServerHttpResponse output) {
        if (user == null) {
            return jsonError(output, HttpStatus.UNAUTHORIZED);
        }
        String sessionId = sessions.resolve(user.getName(), input.session_id());
        Map<String, Object> payload = Map.of(
            "question", input.question(),
            "session_id", sessionId,
            "lang", input.lang() == null ? "uz" : input.lang());

        return client.post().uri("/api/chat/stream")
            .contentType(MediaType.APPLICATION_JSON)
            .accept(MediaType.TEXT_EVENT_STREAM)
            .bodyValue(payload)
            .exchangeToMono(upstream -> {
                if (!upstream.statusCode().is2xxSuccessful()) {
                    HttpStatusCode status = upstream.statusCode().value() == 401
                        ? HttpStatus.BAD_GATEWAY : upstream.statusCode();
                    return upstream.releaseBody().then(jsonError(output, status));
                }
                if (upstream.headers().contentType()
                        .filter(t -> t.isCompatibleWith(MediaType.TEXT_EVENT_STREAM))
                        .isEmpty()) {
                    return upstream.releaseBody().then(
                        jsonError(output, HttpStatus.BAD_GATEWAY));
                }
                output.getHeaders().setContentType(MediaType.TEXT_EVENT_STREAM);
                output.getHeaders().setCacheControl("no-cache, no-transform");
                output.getHeaders().set("X-Accel-Buffering", "no");
                return output.writeAndFlushWith(
                    upstream.bodyToFlux(DataBuffer.class)
                        .doOnDiscard(DataBuffer.class, DataBufferUtils::release)
                        .map(Mono::just));
            })
            .onErrorResume(WebClientRequestException.class, error -> {
                if (output.isCommitted()) return Mono.error(error);
                return jsonError(output, HttpStatus.SERVICE_UNAVAILABLE);
            });
    }

    private Mono<Void> jsonError(ServerHttpResponse output, HttpStatusCode status) {
        output.setStatusCode(status);
        output.getHeaders().setContentType(MediaType.APPLICATION_JSON);
        byte[] json = "{\"detail\":\"Chatbot so'rovini bajarib bo'lmadi\"}"
            .getBytes(StandardCharsets.UTF_8);
        return output.writeWith(Mono.just(output.bufferFactory().wrap(json)));
    }
}
```

Oqim shu `exchangeToMono` ichida to'liq uzatiladi; upstream javob tanasi
undan tashqariga o'qilmagan holda chiqarilmaydi. Har kelgan buffer darhol
flush qilinadi. Brauzer ulanishi uzilsa, reaktiv zanjir upstream obunasini
bekor qiladi. Shuning uchun alohida `subscribe()` chaqirmang.

Mavjud Spring Security qoidalarida `/api/lims/**` autentifikatsiyalangan
foydalanuvchilargagina ochilsin. Cookie sessiya ishlatilsa, frontend mavjud
loyihadagi CSRF tokenini yuborsin. Oqim ishga tushgandan keyin HTTP statusni
almashtirib bo'lmaydi: Python `event: error` yuboradi yoki transport uziladi.

## Qo'shimcha javob maydonlari va sahifalash

`result` da `answer`, `columns`, `rows`, `row_count`, `total_count`,
`truncated`, `next_cursor`, `warnings`, `error`, `route`, `route_reason`,
`blocked_category`, `sql`, `tables`, `fast_path`, `session_id` keladi.
`rows` odatda ustun nomlari kalit bo'lgan obyektlar ro'yxati; bo'sh ro'yxat
ham to'g'ri javob. `total_count` noma'lum bo'lsa `null`.

Sahifalash uchun Python'ga:

```http
POST /api/chat/page
Content-Type: application/json
Authorization: Basic <server tomonda>

{"cursor":"<result.next_cursor>"}
```

Javob: `columns`, `rows`, `row_count`, `next_cursor`. Keyingi sahifa ko'pi
bilan 20 satr. Cursor 15 daqiqa yashaydi va Python jarayoni xotirasida
saqlanadi; restartda yo'qoladi. Keyingi cursor asl muddatni uzaytirmaydi.

Java'da sahifalash qo'shilsa, SSE `result.next_cursor` qiymatini joriy
foydalanuvchi bilan bog'lab saqlang va `/page` oldidan egalikni tekshiring.
Python uni xizmatning Basic loginiga bog'laydi, Java foydalanuvchisiga emas.
Ko'p instansiya uchun umumiy cursor ownership saqlagichi va Python'da
sticky routing yoki umumiy cursor saqlagichi talab etiladi. Yuqoridagi
baytlarni uzatuvchi namuna cursor registrini amalga oshirmaydi.

## Reverse proxy va xatolar

Frontend va Java'ni bitta origin ostida berish uchun Nginx misoli:

```nginx
location /api/lims/ {
    proxy_pass http://java-backend:8081;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
    gzip off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

Java va Python o'rtasida ham proksi bo'lsa, SSE uchun o'sha yerda ham
buffering o'chiriladi. Alohida origin ishlatilsa, CORS'ni React → Java
orasida sozlang; cookie uchun aniq origin va credentials ruxsati kerak.

| Holat | Amal |
|---|---|
| Java 400 | Bo'sh/noto'g'ri savol, til yoki session formatini tekshirish |
| Java 401/403 | Mavjud foydalanuvchi autentifikatsiyasi, CSRF yoki suhbat egaligini tekshirish |
| Python 401 → Java 502 | Java'dagi xizmat login/parolini tekshirish |
| Python 422 | So'rov maydonlari formatini tekshirish |
| 503 | Xizmat, LLM, baza yoki tarmoq holatini tekshirish |
| SSE `error` / `result.error` | UI'da muvaffaqiyatsiz javob sifatida ko'rsatish |
| HTTP 200, `route=blocked` | Rad etish javobini `answer` dan ko'rsatish |
| `/page` 404 / 409 | Cursor eskirgan yoki so'rovni sahifalab bo'lmaydi; savolni qayta berish |

## Qabul qilish tekshiruvi

1. Foydalanuvchi Java tizimiga kirgan holda savol yuboradi; `start` va
   keyin `result` keladi. `delta` bo'lsa ekranda darhol ko'rinadi.
2. Bir xil session bilan davomli savol yuboriladi; yangi suhbatda session
   yuborilmaydi. Boshqa foydalanuvchining sessioni 403 oladi.
3. Brauzerda bekor qilish upstream so'rovini ham to'xtatadi.
4. Noto'g'ri xizmat paroli brauzerga Basic credential yubormasdan xato beradi.
5. Natija HTTP 200 bo'lsa ham `error` tekshiriladi. `result` kelmay uzilgan
   oqim muvaffaqiyat sifatida belgilanmaydi.

Namuna Java ilovasiga qo'shib build va integratsiya testi qilinishi kerak;
bu repoda Java loyiha yo'q. Python wire-format manbalari:
[`api.py`](../app/api.py), [`schemas.py`](../app/schemas.py),
[`auth.py`](../app/auth.py), [`pagination.py`](../app/pagination.py).
