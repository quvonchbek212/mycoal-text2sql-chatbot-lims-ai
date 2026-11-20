"""/api/chat/stream (SSE) testlari: javob tokenlari, sonlar nazorati oqimda, ping, xato, uzilish."""
import asyncio
import json

import anyio
import psycopg
import pytest
from fastapi.testclient import TestClient

import main
from lims_chatbot.app import api, streaming
from lims_chatbot.app.config import Settings
from lims_chatbot.app.graph import NumberGuard
from lims_chatbot.app.memory import ChatMemory
from lims_chatbot.app.schema_provider import SchemaProvider
from lims_chatbot.app.sql_service import DB_UNAVAILABLE, SqlService
from lims_chatbot.tests.test_graph import FakeSql, ScriptLLM, _graph
from lims_chatbot.tests.test_sql_service import FakeDb, FakeLLM, sql

AUTH = ("tester", "maxfiy-parol")


class TokenGraph:
    """Haqiqiy graf kabi javobni bo'laklab chiqaradi."""

    def __init__(self, delay: float = 0.0, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.histories = []

    async def run(self, question, history=None, lang="uz"):
        self.histories.append(list(history or []))
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("maxfiy ichki tafsilot")
        for part in ("Laboratoriyalar ", "soni: ", "65"):
            streaming.delta(part)
            await asyncio.sleep(0.01)
        return {"route": "database", "answer": "Laboratoriyalar soni: 65", "sql": "SELECT 65",
                "columns": ["n"], "rows": [{"n": 65}], "row_count": 1, "tables": ["lab"]}


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        name, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        if name:
            events.append((name, data))
    return events


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        c.app.state.graph = TokenGraph()
        c.app.state.memory = ChatMemory()
        c.app.state.settings = Settings(db_password="x", api_username=AUTH[0], api_password=AUTH[1])
        yield c


def stream(client, **body):
    r = client.post("/api/chat/stream", json=body, auth=AUTH)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    return r, parse_sse(r.text)


# ---------------- endpoint ----------------
def test_stream_sends_answer_tokens_then_result(client):
    _, events = stream(client, question="Laboratoriyalar soni?", session_id="s1")
    names = [n for n, _ in events]
    assert names[0] == "start" and names[-1] == "result"
    assert set(names[1:-1]) == {"delta"}
    assert events[0][1] == {"session_id": "s1"}
    result = events[-1][1]
    assert "".join(d["text"] for n, d in events if n == "delta") == result["answer"]
    assert result["session_id"] == "s1" and result["rows"] == [{"n": 65}]


def test_stream_has_no_internal_process_events(client):
    r, events = stream(client, question="x")
    assert {n for n, _ in events} <= {"start", "delta", "result"}
    assert "stage" not in r.text


def test_stream_generates_session_and_saves_history(client):
    _, events = stream(client, question="birinchi")
    sid = events[0][1]["session_id"]
    assert sid and events[-1][1]["session_id"] == sid
    stream(client, question="davomi", session_id=sid)
    assert client.app.state.graph.histories[-1] == [{"question": "birinchi", "sql": "SELECT 65"}]


def test_stream_heartbeat_while_silent(client, monkeypatch):
    monkeypatch.setattr(api, "HEARTBEAT_SECONDS", 0.05)
    client.app.state.graph = TokenGraph(delay=0.3)
    r, events = stream(client, question="x")
    assert ": ping" in r.text and events[-1][0] == "result"


def test_stream_error_hides_details(client):
    client.app.state.graph = TokenGraph(fail=True)
    r, events = stream(client, question="x")
    assert events[-1][0] == "error" and "maxfiy" not in r.text


def test_stream_validation_before_streaming(client):
    r = client.post("/api/chat/stream", json={"question": ""}, auth=AUTH)
    assert r.status_code == 422


# ---------------- mijoz uzilishi ----------------
class RecordingMemory(ChatMemory):
    def __init__(self):
        super().__init__()
        self.turns = []

    async def add(self, session_id, turn):
        self.turns.append((session_id, turn))
        await super().add(session_id, turn)


class HangingGraph:
    cancelled = False

    async def run(self, question, history=None, lang="uz"):
        streaming.delta("Yarim javob")
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            HangingGraph.cancelled = True
            raise


def test_disconnect_cancels_graph_and_saves_partial_answer():
    memory = RecordingMemory()

    async def go():
        gen = api._chat_events(HangingGraph(), memory, "uzoq savol", "s9")
        assert (await gen.__anext__()).startswith("event: start")
        assert "Yarim javob" in await gen.__anext__()
        await gen.aclose()  # mijoz uzildi
        await asyncio.sleep(0)  # bekor qilish graf taskiga yetib borsin

    asyncio.run(go())
    assert HangingGraph.cancelled
    [(sid, turn)] = memory.turns
    assert (sid, turn.route, turn.answer) == ("s9", "cancelled", "Yarim javob")


def test_concurrent_requests_do_not_mix_tokens():
    async def one(tag):
        got = []
        with streaming.listen(got.append):
            for i in range(3):
                streaming.delta(f"{tag}{i}")
                await asyncio.sleep(0)
        return got

    async def go():
        return await asyncio.gather(one("a"), one("b"))

    a, b = asyncio.run(go())
    assert a == ["a0", "a1", "a2"] and b == ["b0", "b1", "b2"]


def test_delta_without_listener_is_noop():
    assert not streaming.active()
    streaming.delta("x")  # xato yo'q


# ---------------- sonlar nazorati oqimda ----------------
def feed_all(guard, chunks):
    out = "".join(guard.feed(c) for c in chunks)
    return out + guard.feed("", final=True)


def test_guard_passes_supported_numbers_split_across_chunks():
    g = NumberGuard("savol", '{"rows": [{"n": 1472, "foiz": 77.5}]}')
    assert feed_all(g, ["Jami 14", "72 ta, ulushi 77", ",", "5%."]) == "Jami 1472 ta, ulushi 77,5%."
    assert g.bad is None


def test_guard_holds_partial_number_until_complete():
    g = NumberGuard('{"n": 1472}')
    assert g.feed("Jami 14") == "Jami "  # «14» hali tugamagan — ushlab turiladi
    assert g.feed("72 ta") == "1472 ta"


def test_guard_stops_before_unsupported_number_is_shown():
    g = NumberGuard('{"n": 1472}')
    shown = g.feed("Jami 15") + g.feed("00 ta chetlanish")
    assert g.bad == "1500" and "1500" not in shown and "15" not in shown
    assert g.feed(" yana matn") == ""  # rad etilgandan keyin hech narsa chiqmaydi


def test_guard_checks_single_digits_and_final_tail():
    g = NumberGuard('{"n": 12}')
    assert feed_all(g, ["eng muhim 3 tasi: 12"]) == "" and g.bad == "3"
    g = NumberGuard('{"n": 12}')
    assert g.feed("oxirida 99") == "oxirida "
    assert g.feed("", final=True) == "" and g.bad == "99"


# ---------------- graf: javob tokenlari ----------------
class StreamLLM(ScriptLLM):
    """Router — oddiy javob; xulosa/chitchat — tokenlab."""

    def __init__(self, router, tokens):
        super().__init__(router)
        self.tokens = tokens
        self.closed = False
        self.consumed = 0

    async def chat_stream(self, system, user, **kw):
        try:
            for t in self.tokens:
                self.consumed += 1
                yield t
        finally:
            self.closed = True


def run_streaming(graph, question):
    got = []

    async def go():
        with streaming.listen(got.append):
            return await graph.run(question)

    return anyio.run(go), "".join(got)


def test_summary_streams_tokens_then_list(settings):
    llm = StreamLLM({"route": "database", "tables": []}, ["  Chetlanishlar ", "sexlar bo'yicha."])
    state, streamed = run_streaming(_graph(settings, llm, FakeSql()), "chetlanishlar")
    assert streamed == "Chetlanishlar sexlar bo'yicha.\n\n1. Ammiak: n 1472\n2. PVX: n 398" == state["answer"]


def test_symbols_are_not_streamed(settings):
    llm = StreamLLM({"route": "database", "tables": []}, ["**Natija**", " tayyor ✅"])
    state, streamed = run_streaming(_graph(settings, llm, FakeSql()), "chetlanishlar")
    assert "*" not in streamed and "✅" not in streamed
    assert state["answer"].startswith("Natija tayyor\n\n1. Ammiak")


def test_summary_with_invented_number_is_cut_and_replaced(settings):
    llm = StreamLLM({"route": "database", "tables": []}, ["Jami ", "15", "00", " ta", " va ", "yana ", "ko'p"])
    state, streamed = run_streaming(_graph(settings, llm, FakeSql()), "chetlanishlar")
    assert "1500" not in streamed and "15" not in streamed    # noto'g'ri son ekranga chiqmadi
    assert llm.closed and llm.consumed < len(llm.tokens)     # LLM oqimi darhol to'xtatildi
    assert state["answer"].startswith("Jami 2 ta yozuv topildi.")  # yakuniy javob — qoidaviy


def test_chitchat_streams_tokens(settings):
    llm = StreamLLM({"route": "chitchat", "tables": []}, ["Salom", "! Men ", "LIMS yordamchisiman."])
    state, streamed = run_streaming(_graph(settings, llm, FakeSql()), "salom")
    assert streamed == "Salom! Men LIMS yordamchisiman." == state["answer"]


def test_single_row_answer_streams_without_list(settings):
    sql_res = {"sql": "SELECT 1", "columns": ["n"], "rows": [{"tahlillar_soni": 9}], "row_count": 1}
    llm = StreamLLM({"route": "database", "tables": []}, ["Kecha ", "9 ta tahlil ", "o'tkazilgan."])
    state, streamed = run_streaming(_graph(settings, llm, FakeSql(sql_res)), "kecha nechta tahlil?")
    assert streamed == "Tahlillar soni: 9" == state["answer"]


def test_llm_stream_failure_falls_back(settings):
    class Broken(StreamLLM):
        async def chat_stream(self, system, user, **kw):
            yield "Sal"
            raise RuntimeError("uzildi")

    state, _ = run_streaming(_graph(settings, Broken({"route": "chitchat"}, []), FakeSql()), "salom")
    assert state["answer"] == "Salom! Men LIMS yordamchisiman."


# ---------------- baza ulanishi xatosi — qayta urinilmaydi ----------------
def test_connection_error_is_not_retried(settings):
    class DownDb(FakeDb):
        async def run_select(self, sql_text):
            self.executed.append(sql_text)
            raise psycopg.errors.ConnectionTimeout("connection timeout expired")

    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis"), sql("SELECT 2")])
    db = DownDb()
    res = anyio.run(SqlService(settings, llm, db, SchemaProvider(settings, db)).run, "Nechta tahlil bor?")
    assert res["error"] == DB_UNAVAILABLE
    assert len(llm.calls) == 1 and len(db.executed) == 1  # SQL qayta yozdirilmadi


def test_statement_timeout_still_retried(settings):
    class SlowDb(FakeDb):
        async def run_select(self, sql_text):
            self.executed.append(sql_text)
            if len(self.executed) == 1:
                raise psycopg.errors.QueryCanceled("canceling statement due to statement timeout")
            return {"columns": ["n"], "rows": [{"n": 1}], "redacted_columns": []}

    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis"), sql("SELECT count(*) AS n FROM tnb_analysis a")])
    db = SlowDb()
    res = anyio.run(SqlService(settings, llm, db, SchemaProvider(settings, db)).run, "Nechta tahlil bor?")
    assert res["error"] is None and len(llm.calls) == 2  # model tezroq SQL yozib ko'rdi
