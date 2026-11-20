"""Text-to-SQL quvuri testlari — soxta LLM va baza bilan (tarmoqsiz)."""
import anyio
import pytest

from lims_chatbot.app.schema_provider import SchemaProvider
from lims_chatbot.app.sql_service import SqlService


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    async def chat_messages(self, messages, **kw):
        self.calls.append([dict(m) for m in messages])
        return self.replies.pop(0)

    async def chat(self, system, user, **kw):
        return await self.chat_messages([{"role": "system", "content": system}, {"role": "user", "content": user}])


class FakeDb:
    def __init__(self, rows=None, total=None, fail_first=False):
        self.rows = rows if rows is not None else [{"n": 1}]
        self.total = total
        self.fail_first = fail_first
        self.executed: list[str] = []

    async def run_select(self, sql):
        self.executed.append(sql)
        if self.fail_first:
            self.fail_first = False
            raise RuntimeError('column "foo" does not exist\nLINE 1: ...')
        cols = list(self.rows[0]) if self.rows else []
        return {"columns": cols, "rows": list(self.rows), "redacted_columns": []}

    async def count(self, sql):
        return self.total


def _service(settings, llm, db):
    return SqlService(settings, llm, db, SchemaProvider(settings, db))


def sql(text):
    return f"```sql\n{text}\n```"


def test_retry_keeps_question_and_previous_sql(settings):
    llm = FakeLLM([
        sql("SELECT a.sampling_point FROM tnb_analysis a"),
        sql("SELECT count(*) AS n FROM tnb_analysis"),
    ])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "Nechta tahlil bor?")
    assert res["error"] is None and res["sql"] == "SELECT count(*) AS n FROM tnb_analysis"
    second = llm.calls[1]
    assert [m["role"] for m in second] == ["system", "user", "assistant", "user"]
    assert "Nechta tahlil bor?" in second[1]["content"]          # savol unutilmaydi
    assert "a.sampling_point" in second[2]["content"]             # oldingi SQL ko'rinadi
    assert "sampling_point_code" in second[3]["content"]          # aniq tavsiya bilan xato


def test_wrong_value_is_caught_before_database(settings):
    llm = FakeLLM([
        sql("SELECT count(*) AS n FROM tnb_analysis WHERE status = 'chetlanish'"),
        sql("SELECT count(*) AS n FROM tnb_analysis WHERE status = 'Chetlanish'"),
    ])
    db = FakeDb()
    res = anyio.run(_service(settings, llm, db).run, "Chetlanishlar soni")
    assert res["error"] is None
    assert len(db.executed) == 1 and "'Chetlanish'" in db.executed[0]
    assert "Ehtimol: 'Chetlanish'" in llm.calls[1][3]["content"]


def test_same_error_twice_stops_early(settings):
    bad = sql("SELECT foo FROM tnb_analysis")
    llm = FakeLLM([bad, bad, bad])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "savol")
    assert res["error"] and len(llm.calls) == 2


def test_database_error_fed_back(settings):
    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis"), sql("SELECT count(*) AS n FROM lab")])
    res = anyio.run(_service(settings, llm, FakeDb(fail_first=True)).run, "savol")
    assert res["error"] is None
    assert "Baza xatosi" in llm.calls[1][3]["content"]


def test_clarifying_question(settings):
    llm = FakeLLM(["SAVOL: Qaysi davr uchun?"])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "tahlillar")
    assert res["clarify"] == "Qaysi davr uchun?" and res["sql"] is None


def test_truncated_result_reports_total(settings):
    rows = [{"n": i} for i in range(settings.sql_row_limit + 1)]
    llm = FakeLLM([sql("SELECT status AS n FROM tnb_analysis")])
    res = anyio.run(_service(settings, llm, FakeDb(rows=rows, total=4468)).run, "hamma tahlillar")
    assert res["truncated"] and res["row_count"] == settings.sql_row_limit
    assert res["total_count"] == 4468
    assert any("jami 4468" in w for w in res["warnings"])


@pytest.mark.parametrize("question,limit,expected", [
    ("Chetlanishlar ro'yxati", 50, (20, True, 1472)),  # model o'zi qo'ygan LIMIT to'ldi — jami bazadan
    ("Oxirgi 50 ta chetlanish", 50, (20, True, 50)),   # foydalanuvchi so'ragan 50 ta; ko'rsatiladi 20
    ("Eng ko'p chetlanish bo'lgan nuqtalar", 5, (5, False, None)),  # top-N — to'liq
])
def test_model_own_limit_does_not_hide_total(settings, question, limit, expected):
    settings.sql_row_limit = 500
    rows = [{"tahlilchi": f"T{i}"} for i in range(limit)]
    llm = FakeLLM([sql(f"SELECT a.analyst_full_name AS tahlilchi FROM tnb_analysis a LIMIT {limit}")])
    res = anyio.run(_service(settings, llm, FakeDb(rows=rows, total=1472)).run, question)
    assert (res["row_count"], res["truncated"], res["total_count"]) == expected


def test_fast_path_skips_llm(settings):
    llm = FakeLLM([])
    db = FakeDb(rows=[{"kod": "INST-001"}])
    res = anyio.run(_service(settings, llm, db).run, "Kalibrovka muddati o'tgan asboblar")
    assert res["fast_path"] and not llm.calls
    assert "calibration_due_at" in db.executed[0]


def test_history_goes_into_prompt(settings):
    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis")])
    history = [{"question": "Ammiak sexida nechta tahlil?", "sql": "SELECT 1"}]
    anyio.run(_service(settings, llm, FakeDb()).run, "Ulardan nechtasi chetlanish?", None, history)
    assert "OLDINGI SUHBAT" in llm.calls[0][1]["content"]
    assert "Ammiak sexida" in llm.calls[0][1]["content"]


def test_fast_path_disabled_for_follow_ups(settings):
    llm = FakeLLM([sql("SELECT count(*) AS n FROM instrument")])
    history = [{"question": "asboblar", "sql": "SELECT 1"}]
    res = anyio.run(_service(settings, llm, FakeDb()).run, "Kalibrovka muddati o'tgan asboblar", None, history)
    assert not res["fast_path"] and llm.calls


def test_examples_included_in_prompt(settings):
    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis")])
    anyio.run(_service(settings, llm, FakeDb()).run, "Sexlar bo'yicha chetlanishlar soni")
    assert "TEKSHIRILGAN MISOLLAR" in llm.calls[0][0]["content"]


def test_examples_from_another_schema_are_not_sent_to_model(settings, monkeypatch):
    from lims_chatbot.app import sql_catalog

    monkeypatch.setattr(sql_catalog, "CATALOG", [
        sql_catalog.CatalogEntry("Tahlillar eski natijasi", "SELECT old_result FROM tnb_analysis", ("tnb_analysis",)),
        sql_catalog.CatalogEntry("Tahlillar soni", "SELECT count(*) AS n FROM tnb_analysis", ("tnb_analysis",)),
    ])
    llm = FakeLLM([sql("SELECT count(*) AS n FROM tnb_analysis")])
    result = anyio.run(_service(settings, llm, FakeDb()).run, "Tahlillar haqida ma'lumot")
    prompt = llm.calls[0][0]["content"]
    assert result["error"] is None
    assert "old_result" not in prompt
    assert "SELECT count(*) AS n FROM tnb_analysis" in prompt


@pytest.mark.parametrize("bad", ["DELETE FROM lab", "SELECT 1; DROP TABLE lab"])
def test_write_sql_never_executed(settings, bad):
    llm = FakeLLM([sql(bad)] * 3)
    db = FakeDb()
    res = anyio.run(_service(settings, llm, db).run, "savol")
    assert res["error"] and not db.executed


def test_answer_language_hint_and_no_uzbek_fast_path(settings):
    llm = FakeLLM([sql("SELECT count(*) AS количество FROM instrument")])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "Kalibrovka muddati o'tgan asboblar", None, None, "ru")
    assert not res["fast_path"]  # shablon taxalluslari o'zbekcha — ru javobda ishlatilmaydi
    assert "rus tilida" in llm.calls[0][1]["content"]


def test_grouped_counts_get_totals(settings):
    rows = [{"sex": "A", "n": 3}, {"sex": "B", "n": 4}]
    llm = FakeLLM([sql("SELECT a.status AS sex, count(*) AS n FROM tnb_analysis a GROUP BY a.status")])
    res = anyio.run(_service(settings, llm, FakeDb(rows=rows)).run, "holatlar bo'yicha tahlillar")
    assert res["totals"] == {"n": 7}


def test_rows_capped_for_user_but_totals_from_all(settings):
    settings.sql_row_limit = 500
    rows = [{"lab": f"L{i}", "n": 1} for i in range(71)]
    llm = FakeLLM([sql("SELECT a.status AS lab, count(*) AS n FROM tnb_analysis a GROUP BY a.status")])
    res = anyio.run(_service(settings, llm, FakeDb(rows=rows)).run, "laboratoriyalar bo'yicha")
    assert res["row_count"] == 20 and len(res["rows"]) == 20        # API/UI jadvali ham 20 ta
    assert res["truncated"] and res["total_count"] == 71              # jami — hammasidan
    assert res["totals"] == {"n": 71}                                 # «Jami» qatori — hammasidan


_FILTERED = ("SELECT l.name AS lab, count(i.id) AS n FROM lab l JOIN instrument i ON l.id = i.lab_id "
             "WHERE l.is_active GROUP BY l.id, l.name")
_UNFILTERED = ("SELECT l.name AS lab, count(i.id) AS n FROM lab l JOIN instrument i ON l.id = i.lab_id "
               "GROUP BY l.id, l.name")


def test_reference_filter_sent_back_once(settings):
    llm = FakeLLM([sql(_FILTERED), sql(_UNFILTERED)])
    db = FakeDb()
    res = anyio.run(_service(settings, llm, db).run, "Har bir laboratoriyada nechtadan asbob bor?")
    assert res["error"] is None and len(llm.calls) == 2
    assert "guruhlash uchun" in llm.calls[1][3]["content"] and "is_active" not in db.executed[0]


def test_reference_filter_repeated_still_answers(settings):
    llm = FakeLLM([sql(_FILTERED), sql(_FILTERED)])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "Har bir laboratoriyada nechtadan asbob bor?")
    assert res["error"] is None and len(llm.calls) == 2  # javobsiz qolmaydi


def test_reference_filter_allowed_when_user_asks_active(settings):
    llm = FakeLLM([sql(_FILTERED)])
    res = anyio.run(_service(settings, llm, FakeDb()).run, "Faol laboratoriyalarda nechtadan asbob bor?")
    assert res["error"] is None and len(llm.calls) == 1
