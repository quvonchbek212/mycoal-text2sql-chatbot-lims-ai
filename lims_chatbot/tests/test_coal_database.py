"""Regression tests for the new coal schema; fixture has definitions, no data."""
import pathlib

import anyio
import pytest

from lims_chatbot.app.coal_sql_catalog import CATALOG
from lims_chatbot.app.db_client import DataAccessUnavailable, DbClient
from lims_chatbot.app.prompts import build_router_prompt, build_sql_system_prompt
from lims_chatbot.app.schema_catalog import SchemaCatalog
from lims_chatbot.app.schema_provider import SchemaProvider
from lims_chatbot.app.sql_catalog import find_match, similar
from lims_chatbot.app.sql_guard import SqlNotAllowed, check_select, sanitize_select
from lims_chatbot.app.sql_service import SqlService
from lims_chatbot.app.sql_validator import tables_in, validate
from lims_chatbot.tests.test_sql_service import FakeDb, FakeLLM

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "mycoal_schema.json"


@pytest.fixture
def coal_catalog():
    return SchemaCatalog.load(FIXTURE)


@pytest.fixture
def coal_settings(settings):
    return settings.model_copy(update={"schema_file": str(FIXTURE), "schema_char_budget": 24000})


def test_coal_schema_gets_current_notes_and_prompt_rules(coal_catalog):
    assert coal_catalog.profile.name == "coal"
    party = coal_catalog.render_table("tnb_party")
    analysis = coal_catalog.render_table("tnb_analysis")
    assert '"analysisStatus"' in party and "analysis_status" not in party
    assert "sampling_point_code" not in analysis
    assert "tnb_sampling_point_group" not in analysis
    assert "lab_type" in coal_catalog.catalog_line("lab")
    router = build_router_prompt("katalog", coal_catalog.profile)
    prompt = build_sql_system_prompt(analysis, "2026-11-09", profile=coal_catalog.profile)
    for text in (router, prompt):
        assert "laboratory_results" in text
        assert "tnb_methodika" not in text and "tnb_sampling_point_group" not in text


@pytest.mark.parametrize("question,expected", [
    ("Ko'mir namligi", "laboratory_results"),
    ("Качество угля, зольность", "ash_results"),
    ("Coal moisture results", "laboratory_results"),
    ("Vagonlar bo'yicha dalolatnomalar", "calculation_acts"),
    ("Kunlik radiatsiya", "daily_radiations"),
])
def test_coal_table_selection(coal_settings, question, expected):
    provider = SchemaProvider(coal_settings, FakeDb())
    ranked = anyio.run(provider.rank, question)
    assert expected in ranked
    assert all(name not in ranked for name in ("tnb_sampling_point", "tnb_methodika"))


@pytest.mark.parametrize("entry", CATALOG, ids=lambda e: e.question)
def test_coal_templates_match_current_definitions(entry, coal_catalog):
    assert sanitize_select(entry.sql, 10)
    assert validate(entry.sql, coal_catalog) == []
    assert set(tables_in(entry.sql)) == set(entry.tables)


def test_old_ambiguous_analysis_fast_path_is_not_used(coal_catalog):
    assert find_match("Bugun nechta tahlil bo'ldi?", coal_catalog) is None
    entry = find_match("TNB partiyalari tahlil holati bo'yicha soni", coal_catalog)
    assert entry is not None and '"analysisStatus"' in entry.sql
    assert all(not validate(e.sql, coal_catalog) for e in similar("tahlil holati", 3, coal_catalog))


def test_coal_fast_path_executes_with_no_llm(coal_settings):
    llm, db = FakeLLM([]), FakeDb(rows=[{"natijalar_soni": 3}])
    result = anyio.run(SqlService(coal_settings, llm, db).run,
                      "Bugun nechta ko'mir laboratoriya natijasi qayd etilgan?")
    assert result["fast_path"] and result["error"] is None and not llm.calls
    assert "FROM laboratory_results" in db.executed[0]
    assert "tnb_analysis" not in db.executed[0]


@pytest.mark.parametrize("question", [
    "Ish jurnalida nechta alohida ekskavator bor?",
    "Ish jurnalida qancha noyob ekskavatorlar bor?",
    "ish jurnalida nechta ekskavatrlar",
    "Ish jurnalidagi alohida ekskavatorlar soni",
    "Jami ekskavatorlar nechta?",
    "jami ekskavatrlar nechta",
    "Jami nechta ekskavator bor?",
    "Ekskavatorlar qancha?",
    "Jami ekskavatorlar soni",
])
def test_work_log_count_matches_explicit_questions(question, coal_catalog):
    entry = find_match(question, coal_catalog)
    assert entry is not None and entry.tables == ("daily_excavator_work",)


@pytest.mark.parametrize("question", [
    "Bugun ish jurnalida nechta alohida ekskavator bor?",
    "Ish jurnalida nechta alohida ishlayotgan ekskavator bor?",
    "Ish jurnalida nechta alohida ekskavator bor faqat birinchi smenada?",
    "Ma'lumotnomadagi jami ekskavatorlar nechta?",
    "Bugun jami ekskavatorlar nechta?",
    "Jami ishlayotgan ekskavatorlar nechta?",
])
def test_work_log_template_does_not_discard_constraints(question, coal_catalog):
    assert find_match(question, coal_catalog) is None


@pytest.mark.parametrize("count", [42, 7])
@pytest.mark.parametrize("question", [
    "Ish jurnalida nechta alohida ekskavator bor?",
    "Jami ekskavatorlar nechta?",
    "jami ekskavatrlar nechta",
])
def test_work_log_answer_uses_current_database_count_without_llm(coal_settings, count, question):
    from lims_chatbot.app.graph import AssistantGraph

    llm = FakeLLM([])
    db = FakeDb(rows=[{"ish_jurnalidagi_alohida_ekskavatorlar_soni": count}])
    provider = SchemaProvider(coal_settings, db)
    service = SqlService(coal_settings, llm, db, provider)
    graph = AssistantGraph(coal_settings, llm, service, provider)
    result = anyio.run(graph.run, question)
    assert result["fast_path"] and not result.get("error")
    assert result["answer"] == f"Ish jurnalidagi alohida ekskavatorlar soni: {count}"
    assert not llm.calls


def test_work_log_query_deduplicates_dates_and_shifts(coal_catalog):
    import sqlite3

    entry = find_match("Ish jurnalida nechta alohida ekskavator bor?", coal_catalog)
    with sqlite3.connect(":memory:") as conn:
        conn.execute("CREATE TABLE daily_excavator_work (excavator_number TEXT, work_date TEXT, shift INTEGER)")
        conn.executemany("INSERT INTO daily_excavator_work VALUES (?, ?, ?)", [
            ("E-1", "2026-11-08", 1), ("E-1", "2026-11-09", 1),
            ("E-1", "2026-11-09", 2), ("E-2", "2026-11-09", 1),
        ])
        assert conn.execute(entry.sql).fetchone()[0] == 2


def test_ambiguous_analysis_uses_coal_prompt_and_can_clarify(coal_settings):
    llm = FakeLLM(["SAVOL: Ko'mir laboratoriya natijalari yoki TNB tahlillari kerakmi?"])
    db = FakeDb()
    result = anyio.run(SqlService(coal_settings, llm, db).run, "Bugun nechta tahlil bo'ldi?")
    assert result["clarify"] and not result["fast_path"] and not db.executed
    prompt = llm.calls[0][0]["content"]
    assert "laboratory_results" in prompt
    assert "sampling_point_code" not in prompt and "tnb_methodika" not in prompt


def test_runtime_does_not_add_inferred_legacy_relations(coal_catalog):
    # source_* fields exist but are not declared FKs in the inspected coal DB.
    assert not coal_catalog.table("tnb_certificate").fks
    assert not any(fk.get("logical") for t in coal_catalog.tables.values() for fk in t.fks)


def test_database_dates_use_tashkent(coal_settings):
    assert "timezone=Asia/Tashkent" in DbClient(coal_settings).conn_kwargs()["options"]


@pytest.mark.parametrize("query", [
    "SELECT signature_png AS image FROM tnb_sample",
    "SELECT rendered_html AS document FROM tnb_certificate",
])
def test_text_storage_does_not_expose_previously_blocked_documents(query, real_catalog):
    assert validate(query, real_catalog)
    with pytest.raises(SqlNotAllowed):
        check_select(query)


def test_coal_acceptance_queries_match_live_schema(real_catalog):
    from lims_chatbot.tools.coal_eval_set import EVAL_SET
    assert real_catalog.profile.name == "coal"
    for item in EVAL_SET:
        for query in item["gold"]:
            assert validate(query, real_catalog) == [], item["q"]


def test_chitchat_survives_unavailable_schema(coal_settings):
    from lims_chatbot.app.graph import AssistantGraph
    from lims_chatbot.tests.test_graph import FakeSql, ScriptLLM

    class UnavailableSchema:
        async def catalog(self):
            raise DataAccessUnavailable("missing grants")

    llm = ScriptLLM({"route": "chitchat", "tables": []}, "Salom!")
    graph = AssistantGraph(coal_settings, llm, FakeSql(), UnavailableSchema())
    state = anyio.run(graph.run, "Salom")
    assert state["route"] == "chitchat" and state["answer"] == "Salom!"


def test_missing_read_permissions_report_access_error_without_llm(coal_settings):
    class DeniedDb(FakeDb):
        async def introspect_catalog(self):
            raise DataAccessUnavailable("no SELECT grants")

    coal_settings.schema_refresh_seconds = 600
    db, llm = DeniedDb(), FakeLLM([])
    service = SqlService(coal_settings, llm, db)

    async def run_twice():
        for _ in range(2):
            result = await service.run(CATALOG[0].question)
            assert result["error_kind"] == "data_access_unavailable"

    anyio.run(run_twice)
    assert not llm.calls and not db.executed
