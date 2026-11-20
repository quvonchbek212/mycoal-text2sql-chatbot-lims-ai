"""Security and correctness regressions from the November LIMS audit."""
import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import anyio
import pytest

from lims_chatbot.app import db_client
from lims_chatbot.app.answer_format import format_rows
from lims_chatbot.app.config import Settings
from lims_chatbot.app.db_client import DataAccessUnavailable, DbClient, ResultTooLarge, decode_json_object, jsonable
from lims_chatbot.app.graph import AssistantGraph
from lims_chatbot.app.memory import ChatMemory, Turn
from lims_chatbot.app.pagination import QueryPages
from lims_chatbot.app.schema_catalog import Column, SchemaCatalog, Table
from lims_chatbot.app.schema_provider import SchemaProvider
from lims_chatbot.app.sql_catalog import find_match
from lims_chatbot.app.sql_guard import SqlNotAllowed, check_select
from lims_chatbot.app.sql_service import SqlService, history_block
from lims_chatbot.app.sql_validator import validate
from lims_chatbot.tests.test_graph import FakeSql, ScriptLLM, _graph
from lims_chatbot.tests.test_sql_service import FakeDb, FakeLLM
from lims_chatbot.tools.evaluate import compare


@pytest.mark.parametrize("sql", [
    "SELECT row_to_json(u) FROM core_user u",
    "SELECT to_jsonb(u) FROM core_user u",
    "SELECT u::text FROM core_user u",
    "SELECT public.core_user::text FROM public.core_user",
    "SELECT id FROM core_user AS u(ignored,id)",
    "WITH u AS (SELECT id, full_name FROM core_user) SELECT id FROM u(x,id)",
    "SELECT table_to_xml('public.core_user',true,false,'')",
    "SELECT pg_advisory_lock(1)",
    "SELECT pg_sleep_for('1 second')",
    "SELECT lo_get(1)",
    "SELECT public.lower('x')",
    "SELECT id OPERATOR(public.+) id FROM core_user",
    "SELECT id::public.customtype FROM core_user",
    "SELECT array_agg(id) FROM core_user",
    "SELECT string_agg(full_name, ',') FROM core_user",
    "SELECT * FROM core_user",
    "SELECT u.* FROM core_user u",
])
def test_unsafe_sql_never_reaches_db(sql, monkeypatch):
    connect = MagicMock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr(db_client.psycopg, "connect", connect)
    db = DbClient(Settings(_env_file=None))
    with pytest.raises(SqlNotAllowed):
        db._run_select_sync(sql)
    connect.assert_not_called()


@pytest.mark.parametrize("sql", ["DELETE FROM core_user", "SELECT pg_sleep(1)"])
def test_count_also_enforces_guard(sql, monkeypatch):
    connect = MagicMock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr(db_client.psycopg, "connect", connect)
    with pytest.raises(SqlNotAllowed):
        DbClient(Settings(_env_file=None))._count_sync(sql)
    connect.assert_not_called()


@pytest.fixture
def json_catalog():
    return SchemaCatalog(tables={"users": Table("users", None, [
        Column("id", "integer"), Column("data", "jsonb"), Column("password_hash", "text", sensitive=True),
    ])})


@pytest.mark.parametrize("sql", [
    "SELECT data['password_hash']::text FROM users",
    "SELECT concat('payload=', data::text) FROM users",
    "SELECT substring(data::text FROM 2) FROM users",
    "WITH x AS (SELECT data FROM users) SELECT concat('payload=',data::text) FROM x",
    "WITH x AS (SELECT data AS payload FROM users) SELECT payload::text FROM x",
    "SELECT x.data::text FROM (SELECT data FROM users UNION ALL SELECT data FROM users) x",
    "SELECT concat('payload=', (SELECT data FROM users LIMIT 1)::text) FROM users",
    "SELECT substring((SELECT data FROM users LIMIT 1)::text FROM 2)",
    "SELECT concat('payload=',x::text) FROM (SELECT NULL AS x UNION ALL SELECT data AS y FROM users) q",
    "SELECT concat('payload=',x::text) FROM (SELECT NULL AS x UNION ALL SELECT data FROM users) q",
])
def test_json_transformations_keep_lineage(sql, json_catalog):
    assert validate(sql, json_catalog)


def test_plain_json_is_recursively_masked_and_arrays_bounded(json_catalog):
    assert validate("SELECT data FROM users", json_catalog) == []
    for value in [{"profile": {"password_hash": "canary", "name": "safe"}},
                  '{"profile":{"password_hash":"canary","name":"safe"}}']:
        assert jsonable(value) == {"profile": {"password_hash": "***", "name": "safe"}}
    assert jsonable({"accessToken": "canary", "API-Key": "canary", "name": "safe"}) == {
        "accessToken": "***", "API-Key": "***", "name": "safe"}
    with pytest.raises(ResultTooLarge):
        jsonable(list(range(100_000)))
    value = {}
    for _ in range(20):
        value = {"nested": value}
    with pytest.raises(ResultTooLarge):
        jsonable(value)


def test_object_json_is_decoded_bounded_and_masked():
    assert decode_json_object(b'{"result":1.5,"access_token":"canary"}') == {"result": 1.5, "access_token": "***"}
    with pytest.raises(ResultTooLarge):
        decode_json_object(b'x' * 100_001)
    with pytest.raises(ValueError, match="JSON"):
        decode_json_object(b'not-json')


def test_oid_json_only_allows_direct_business_column_projection(oid_catalog):
    assert validate("SELECT inputs_json FROM tnb_analysis", oid_catalog) == []
    assert validate("SELECT sections_json AS results FROM tnb_analysis", oid_catalog) == []
    assert validate("SELECT inputs_json::text FROM tnb_analysis", oid_catalog)
    assert validate("SELECT signature_png FROM tnb_sample", oid_catalog)
    assert validate("WITH x AS (SELECT inputs_json AS payload FROM tnb_analysis) SELECT payload::text FROM x", oid_catalog)


def test_direct_db_caller_cannot_bypass_json_validation(json_catalog, monkeypatch):
    db = DbClient(Settings(_env_file=None))
    db._catalog_cache = json_catalog
    db._catalog_loaded_at = time.monotonic()
    connection = MagicMock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr(db_client.psycopg, "connect", connection)
    with pytest.raises(SqlNotAllowed):
        db._run_select_sync("SELECT concat('payload=', data::text) FROM users")
    connection.assert_not_called()


@pytest.mark.parametrize("origin,allowed", [
    (("public", "tnb_analysis", "inputs_json"), True),
    (("public", "tnb_sample", "signature_png"), False),
    (("other", "tnb_analysis", "inputs_json"), False),
])
def test_object_reader_checks_db_origin_before_reading(oid_catalog, monkeypatch, origin, allowed):
    conn = MagicMock()
    conn.__enter__.return_value = conn
    cur = MagicMock()
    cur.__enter__.return_value = cur
    conn.cursor.return_value = cur
    cur.description = [SimpleNamespace(name="payload", type_code=26)]
    cur.fetchmany.return_value = [{"payload": 123}]
    cur.pgresult.ftable.return_value = 10
    cur.pgresult.ftablecol.return_value = 2
    metadata = MagicMock()
    metadata.fetchone.return_value = origin
    data = MagicMock()
    data.fetchone.return_value = (b'{"result":1.25,"password":"synthetic-canary"}',)
    conn.execute.side_effect = [metadata, data]
    monkeypatch.setattr(db_client.psycopg, "connect", lambda **kw: conn)
    db = DbClient(Settings(_env_file=None))
    db._catalog_cache = oid_catalog
    db._catalog_loaded_at = time.monotonic()
    if allowed:
        result = db._run_select_sync("SELECT inputs_json AS payload FROM tnb_analysis LIMIT 1")
        assert result["rows"] == [{"payload": {"result": 1.25, "password": "***"}}]
        assert conn.execute.call_args.args[1] == (123, 100_001)
    else:
        with pytest.raises(ValueError, match="OID"):
            db._run_select_sync("SELECT inputs_json AS payload FROM tnb_analysis LIMIT 1")
        assert conn.execute.call_count == 1


def test_safe_controls_and_nested_aliases(catalog):
    for sql in [
        "SELECT count(*) FROM core_user",
        "SELECT a.sampling_point_code FROM tnb_analysis a WHERE EXISTS (SELECT 1 FROM lab a WHERE a.is_active)",
        "SELECT count(*) FROM tnb_analysis WHERE status <> 'unknown'",
        "SELECT count(*) FROM tnb_analysis WHERE status NOT IN ('unknown')",
        "SELECT count(*) FROM public.lab",
        "SELECT q.id FROM (SELECT id FROM lab) q",
        "WITH q AS (SELECT id FROM lab) SELECT q.id FROM q",
    ]:
        assert check_select(sql)
        assert validate(sql, catalog) == []
    assert validate("SELECT count(*) FROM other.lab", catalog)
    assert validate("SELECT count(*) FROM tnb_analysis a WHERE status='unknown'", catalog)


def test_function_lookup_cannot_fall_back_to_application_schema(catalog):
    db = DbClient(Settings(_env_file=None))
    db._catalog_cache = catalog
    db._catalog_loaded_at = time.monotonic()
    query = db._checked_sync("WITH x AS (SELECT id FROM lab) SELECT id FROM x")
    assert "FROM public.lab" in query and "FROM x" in query and "public.x" not in query
    assert "search_path=pg_catalog " in db.conn_kwargs()["options"] + " "
    assert "search_path=pg_catalog,public" not in db.conn_kwargs()["options"]


@pytest.mark.parametrize("question", [
    "Bugun nechta tahlil Ammiak sexida o'tkazildi?",
    "Ochiq nomuvofiqliklar faqat sentyabr uchun",
    "Kalibrovka muddati o'tgan asboblar faqat 912 laboratoriyada",
])
def test_fast_path_preserves_extra_constraints(question):
    assert find_match(question) is None


def test_scalar_answer_never_uses_model_number(settings):
    llm = ScriptLLM({"route": "database", "tables": []}, "Jami 9 ta tahlil bor.")
    result = FakeSql({"sql": "SELECT 0 AS n", "columns": ["n"], "rows": [{"n": 0}], "row_count": 1})
    state = anyio.run(_graph(settings, llm, result).run, "nechta?")
    assert state["answer"] == "N: 0" and len(llm.systems) == 1


@pytest.mark.parametrize("value", [123, "lab", {}, [1]])
def test_invalid_router_shapes_recover(settings, value):
    state = anyio.run(_graph(settings, ScriptLLM({"route": "database", "tables": value}), FakeSql()).run, "nechta?")
    assert state["route"] == "database"
    assert isinstance(state["tables"], list)


def test_clarification_survives_next_turn():
    async def go():
        memory = ChatMemory()
        await memory.add("s", Turn("Tahlillar soni?", "Qaysi davr?", "database",
            meta={"clarification": "Qaysi davr?"}))
        await memory.add("s", Turn("xato", "", "database", sql="SELECT 1", error="failed"))
        return await memory.history("s")
    history = anyio.run(go)
    assert len(history) == 1
    assert "Tahlillar soni?" in history_block(history) and "Qaysi davr?" in history_block(history)


def test_failed_count_does_not_invent_exact_total(settings):
    class NoCount(FakeDb):
        async def count(self, sql):
            raise TimeoutError()
    settings.sql_row_limit = 500
    db = NoCount(rows=[{"id": i} for i in range(50)])
    result = {"warnings": [], "totals": {}}
    service = SqlService(settings, FakeLLM([]), db)
    anyio.run(service._execute, "SELECT id FROM lab LIMIT 50", result, "Laboratoriyalar")
    assert result["truncated"] and result["total_count"] is None
    assert "jami 50" not in " ".join(result["warnings"])


def test_missing_object_permission_is_not_rewritten_as_other_data(settings):
    class DeniedDb(FakeDb):
        async def run_select(self, query):
            self.executed.append(query)
            raise DataAccessUnavailable("denied")
    db = DeniedDb()
    llm = FakeLLM(["SELECT inputs_json FROM tnb_analysis", "SELECT id FROM tnb_analysis"])
    result = anyio.run(SqlService(settings, llm, db).run, "Tahlilning o'lchangan qiymatlari")
    assert result["error_kind"] == "data_access_unavailable"
    assert len(llm.calls) == len(db.executed) == 1


def test_totals_line_is_not_an_extra_record():
    result = {"rows": [{"n": i} for i in range(20)], "totals": {"n": 190},
              "truncated": True, "total_count": 30}
    assert "Birinchi 20 tasi" in format_rows(result)


def test_evaluation_rejects_matching_id_or_total_with_wrong_values():
    assert not compare("scalar", [(12,)], [{"id": 12, "actual_count": 999}], 1)[0]
    assert not compare("rows_subset", [("A", 1), ("B", 2)], [{"name": "WRONG", "n": 999}], 1, 2)[0]
    assert not compare("overlap80", [("A", 1)], [{"name": "A", "n": 999}], 1)[0]
    assert compare("rows_subset", [("A", 1), ("B", 2)], [{"name": "A", "n": 1}], 1, 2)[0]
    assert compare("scalar", [(12,)], [{"count": 12}], 1)[0]
    assert compare("rows_subset", [("A", 1), ("B", 2)],
                   [{"code": "A", "name": "alpha", "count": 1}, {"code": "B", "name": "beta", "count": 2}], 2)[0]
    assert not compare("rows_subset", [("A", 1), ("B", 2)],
                       [{"code": "A", "count": 1}, {"count": 2, "code": "B"}], 2)[0]


def test_cursors_are_user_bound_expiring_and_read_only(monkeypatch):
    pages = QueryPages()
    token = pages.add("SELECT id FROM lab ORDER BY id", ["id"], 20, "alice")
    page = pages.get(token, "alice")
    assert "OFFSET 20" in pages.query(page)
    with pytest.raises(ValueError):
        pages.get(token, "bob")
    with pytest.raises(SqlNotAllowed):
        pages.add("SELECT pg_sleep(1)", ["id"], 20, "alice")
    monkeypatch.setattr(time, "monotonic", lambda: page.expires_at + 1)
    with pytest.raises(ValueError):
        pages.get(token, "alice")


def test_page_preserves_order_offset_and_user_limit():
    pages = QueryPages()
    token = pages.add("SELECT id FROM lab ORDER BY id DESC LIMIT 25 OFFSET 5", ["id"], 20, "alice")
    query = pages.query(pages.get(token, "alice"))
    assert "ORDER BY id DESC" in query and "LIMIT 5" in query and "OFFSET 25" in query


def test_file_snapshot_refreshes_from_live_metadata(settings):
    class LiveDb:
        async def introspect_catalog(self):
            return SchemaCatalog(tables={"new_table": Table("new_table", None, [Column("new_column", "text")])})
    settings.schema_refresh_seconds = 600
    provider = SchemaProvider(settings, LiveDb())
    catalog = anyio.run(provider.catalog)
    assert list(catalog.tables) == ["new_table"]
    assert provider.live_verified and provider.source == "live-metadata"
