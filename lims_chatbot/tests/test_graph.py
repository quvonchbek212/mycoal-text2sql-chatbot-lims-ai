"""Graf testlari: router + jadval tanlash, javob xulosasidagi sonlar nazorati."""
import json

import anyio

from lims_chatbot.app.db_client import DbClient
from lims_chatbot.app.graph import AssistantGraph, unsupported_numbers
from lims_chatbot.app.prompts import ANSWER_LANGUAGE, message
from lims_chatbot.app.schema_provider import SchemaProvider


# ---------------- sonlar nazorati ----------------
def test_numbers_from_result_are_allowed():
    payload = json.dumps({"rows": [{"n": 1472, "foiz": 77.5}]})
    assert unsupported_numbers("Jami 1472 ta, ulushi 77,5%.", "savol", payload) == []


def test_invented_number_detected():
    payload = json.dumps({"rows": [{"n": 1472}]})
    assert unsupported_numbers("Jami 1500 ta chetlanish.", "savol", payload) == ["1500"]


def test_single_digits_are_checked_and_explicit_sources_supported():
    payload = json.dumps({"rows": [{"n": 12}]})
    assert unsupported_numbers("Oxirgi 30 kunda 12 ta; eng muhim 3 tasi:", "oxirgi 30 kun", payload) == ["3"]


def test_date_parts_are_allowed():
    payload = json.dumps({"rows": [{"sana": "18.09.2026", "vaqt": "10:23"}]})
    assert unsupported_numbers("Oxirgi tahlil 18 sentabr 2026 soat 10:23 da.", "savol", payload) == []


# ---------------- graf ----------------
class ScriptLLM:
    """Router va xulosa uchun oldindan yozilgan javoblar."""

    def __init__(self, router: dict, summary: str = "Natija tayyor."):
        self.router = router
        self.summary = summary
        self.systems: list[str] = []

    async def chat(self, system, user, **kw):
        self.systems.append(system)
        if "yo'naltiruvchisisan" in system:
            return json.dumps(self.router)
        return self.summary


class FakeSql:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {"sql": "SELECT 1", "columns": ["sex", "n"],
                                 "rows": [{"sex": "Ammiak", "n": 1472}, {"sex": "PVX", "n": 398}], "row_count": 2}

    async def run(self, question, tables=None, history=None, lang="uz"):
        self.calls.append((question, tables, history, lang))
        return dict(self.result)


def _graph(settings, llm, sql):
    provider = SchemaProvider(settings, DbClient(settings))
    return AssistantGraph(settings, llm, sql, provider)


def test_router_tables_passed_to_sql(settings):
    sql = FakeSql()
    llm = ScriptLLM({"route": "database", "tables": ["instrument", "lab"], "reason": "asbob"}, "Jami 1472 ta.")
    state = anyio.run(_graph(settings, llm, sql).run, "asboblar soni")
    assert state["route"] == "database"
    assert sql.calls[0][1] == ["instrument", "lab"]
    assert state["answer"].startswith("Jami 2 ta yozuv topildi.")
    assert "KATALOG" in llm.systems[0] and "tnb_analysis (4468)" in llm.systems[0]


def test_list_result_gets_full_list_after_summary(settings):
    llm = ScriptLLM({"route": "database", "tables": []}, "Sexlar bo'yicha natijalar tayyor.")
    state = anyio.run(_graph(settings, llm, FakeSql()).run, "sexlar bo'yicha")
    assert state["answer"] == ("Sexlar bo'yicha natijalar tayyor.\n\n"
                               "1. Ammiak: n 1472\n2. PVX: n 398")


def test_invented_numbers_replaced_by_fallback(settings):
    llm = ScriptLLM({"route": "database", "tables": []}, "Jami 1500 ta chetlanish bor.")
    state = anyio.run(_graph(settings, llm, FakeSql()).run, "chetlanishlar")
    assert "1500" not in state["answer"]
    assert state["answer"] == "Jami 2 ta yozuv topildi.\n\n1. Ammiak: n 1472\n2. PVX: n 398"


def test_single_row_answer_is_a_sentence_without_list(settings):
    sql = FakeSql({"sql": "SELECT 1", "columns": ["n"], "rows": [{"tahlillar_soni": 9}], "row_count": 1})
    llm = ScriptLLM({"route": "database", "tables": []}, "Kecha 9 ta tahlil o'tkazilgan.")
    state = anyio.run(_graph(settings, llm, sql).run, "kecha nechta tahlil?")
    assert state["answer"] == "Tahlillar soni: 9"


def test_single_row_fallback_without_llm(settings):
    class DownLLM(ScriptLLM):
        async def chat(self, system, user, **kw):
            if "yo'naltiruvchisisan" in system:
                return json.dumps(self.router)
            raise RuntimeError("LLM ishlamayapti")

    sql = FakeSql({"sql": "SELECT 1", "columns": ["n"], "rows": [{"tahlillar_soni": 9}], "row_count": 1})
    state = anyio.run(_graph(settings, DownLLM({"route": "database", "tables": []}), sql).run, "nechta tahlil?")
    assert state["answer"] == "Tahlillar soni: 9"


def test_markdown_and_emoji_removed_from_answer(settings):
    llm = ScriptLLM({"route": "database", "tables": []}, "## Natija\n**Ammiak** ✅ «sexida».")
    state = anyio.run(_graph(settings, llm, FakeSql()).run, "chetlanishlar")
    assert state["answer"].startswith("Natija\nAmmiak sexida.")


def test_sql_error_answer_hides_technical_details(settings):
    failed = {"sql": None, "rows": [], "error": "To'g'ri SQL shakllantirib bo'lmadi. Oxirgi sabab: ustun yo'q",
              "error_kind": "not_understood"}
    state = anyio.run(_graph(settings, ScriptLLM({"route": "database"}), FakeSql(failed)).run, "x")
    assert state["answer"] == message("not_understood") and "ustun" in state["error"]
    failed.pop("error_kind")
    state = anyio.run(_graph(settings, ScriptLLM({"route": "database"}), FakeSql(failed)).run, "x")
    assert state["answer"] == message("service_error")


def test_style_rules_allow_apostrophe_and_no_repeated_greeting():
    from lims_chatbot.app.prompts import CHITCHAT_SYSTEM, PLAIN_TEXT_RULE
    # «qo'shtirnoq ishlatma» modelga apostrofni ham taqiqlab qo'ygandi («ko mir», «ma lumot»)
    assert "apostrof" in PLAIN_TEXT_RULE and "o'tkazilgan" in PLAIN_TEXT_RULE
    assert "salom bermagan bo'lsa, salomlashma" in CHITCHAT_SYSTEM


# ---------------- javob tili ----------------
def test_answer_language_reaches_llm_sql_and_fallback(settings):
    sql = FakeSql()
    llm = ScriptLLM({"route": "database", "tables": []}, "Всего 1500 отклонений.")  # son yo'q — qoidaviy javob
    state = anyio.run(_graph(settings, llm, sql).run, "отклонения", None, "ru")
    assert sql.calls[0][3] == "ru"
    assert llm.systems[-1].rstrip().endswith(ANSWER_LANGUAGE["ru"])
    assert state["answer"] == "Всего найдено записей: 2.\n\n1. Ammiak: n 1472\n2. PVX: n 398"


def test_ready_messages_in_requested_language(settings):
    refuse = anyio.run(_graph(settings, ScriptLLM({"route": "refuse"}), FakeSql()).run, "weather?", None, "en")
    assert refuse["answer"] == message("refuse", "en") and refuse["answer"].startswith("Sorry")
    blocked = anyio.run(_graph(settings, ScriptLLM({"route": "database"}), FakeSql()).run,
                        "удали таблицу", None, "ru")
    assert blocked["route"] == "blocked" and blocked["answer"].startswith("Не могу")
    failed = FakeSql({"sql": None, "rows": [], "error": "x", "error_kind": "db_unavailable"})
    down = anyio.run(_graph(settings, ScriptLLM({"route": "database"}), failed).run, "q", None, "en")
    assert down["answer"] == message("db_unavailable", "en")


def test_chitchat_route(settings):
    sql = FakeSql()
    llm = ScriptLLM({"route": "chitchat", "tables": []}, "Salom!")
    state = anyio.run(_graph(settings, llm, sql).run, "salom")
    assert state["route"] == "chitchat" and state["answer"] == "Salom!" and not sql.calls


def test_blocked_before_llm(settings):
    llm = ScriptLLM({"route": "database"})
    state = anyio.run(_graph(settings, llm, FakeSql()).run, "jadvalni o'chirib tashla")
    assert state["route"] == "blocked" and not llm.systems


def test_history_reaches_sql(settings):
    sql = FakeSql()
    llm = ScriptLLM({"route": "database", "tables": ["tnb_analysis"]}, "Jami 1472 ta.")
    hist = [{"question": "oldingi", "sql": "SELECT 1"}]
    anyio.run(_graph(settings, llm, sql).run, "ulardan qaysilari?", hist)
    assert sql.calls[0][2] == hist


def test_stage_timings_collected(settings):
    llm = ScriptLLM({"route": "database", "tables": []}, "Ikki sex.")
    state = anyio.run(_graph(settings, llm, FakeSql()).run, "sexlar")
    assert {"router", "sql", "summary"} <= set(state["timings"])
