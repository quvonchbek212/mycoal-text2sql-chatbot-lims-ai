"""Sxema tanlash testlari — to'liq DDL (~150 KB) promptga sig'maydi.

Router tanlagan jadvallar + FK qo'shnilari byudjet ichida olinishi, router
jadval bermasa — leksik zaxira tanlov ishlashi kerak.
"""
import anyio
import pytest
import json
from pathlib import Path

from lims_chatbot.app.config import Settings
from lims_chatbot.app.db_client import DbClient
from lims_chatbot.app.schema_provider import SchemaProvider


def _provider(settings) -> SchemaProvider:
    return SchemaProvider(settings, DbClient(settings))


def test_router_tables_and_fk_neighbours(settings):
    bundle = anyio.run(_provider(settings).bundle, "asboblar holati", ["instrument"])
    # instrument → lab, status_dictionary FK lari qo'shiladi
    assert {"instrument", "lab", "status_dictionary"} <= set(bundle.tables)
    assert bundle.source == "schema-file"
    assert bundle.partial


def test_block_order_is_stable_for_prefix_cache(settings):
    provider = _provider(settings)
    a = anyio.run(provider.bundle, "x", ["instrument", "tnb_analysis"])
    b = anyio.run(provider.bundle, "x", ["tnb_analysis", "instrument"])
    assert a.text == b.text and a.tables[0] == "tnb_analysis"


def test_general_module_table_brings_main_tnb_table(settings):
    path = Path(settings.schema_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tables"]["batch"] = {"columns": [{"name": "id", "type": "uuid"}]}
    path.write_text(json.dumps(data), encoding="utf-8")
    bundle = anyio.run(_provider(settings).bundle, "List of batches by status", ["batch", "status_dictionary"])
    assert {"batch", "tnb_party"} <= set(bundle.tables)


def test_neighbours_skip_always_null_and_empty_tables(settings):
    path = Path(settings.schema_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    analysis = data["tables"]["tnb_analysis"]
    analysis["columns"].append({"name": "party_id", "type": "varchar"})
    analysis["fks"] += [
        {"column": "party_id", "ref_table": "tnb_party", "ref_column": "id"},
        {"column": "lab_sample_id", "ref_table": "lab_sample", "ref_column": "id"},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    bundle = anyio.run(_provider(settings).bundle, "tahlillar", ["tnb_analysis"])
    # tnb_analysis.lab_sample_id doim NULL, lab_sample bo'sh — foydasiz qo'shni
    assert "tnb_party" in bundle.tables and "lab_sample" not in bundle.tables


def test_logical_fk_neighbours(settings):
    bundle = anyio.run(_provider(settings).bundle, "tahlillar", ["tnb_analysis"])
    assert "tnb_sampling_point" in bundle.tables


def test_unknown_router_tables_ignored(settings):
    bundle = anyio.run(_provider(settings).bundle, "tahlillar soni", ["yoq_jadval"])
    assert "yoq_jadval" not in bundle.tables
    assert "tnb_analysis" in bundle.tables  # leksik zaxira (sinonim: tahlil)


def test_budget_respected(schema_file):
    settings = Settings(schema_file=str(schema_file), db_password="x", schema_char_budget=900)
    bundle = anyio.run(_provider(settings).bundle, "asboblar", ["instrument"])
    assert "instrument" in bundle.tables  # asosiy jadval doim kiradi
    assert len(bundle.text) <= 900 + len(bundle.text.split("\n\n")[0])


def test_rank_uses_synonyms(settings):
    ranked = anyio.run(_provider(settings).rank, "Oxirgi haftada nechta chetlanish bo'lgan?")
    assert ranked and ranked[0] == "tnb_analysis"


def test_rank_ignores_noise(settings):
    ranked = anyio.run(_provider(settings).rank, "asbob kalibrovkasi")
    assert ranked[0] == "instrument"
    assert not any(t.startswith("noise_table") for t in ranked)


def test_defaults_when_nothing_matches(settings):
    bundle = anyio.run(_provider(settings).bundle, "qwerty xyz", None)
    assert "tnb_analysis" in bundle.tables


def test_listing_marks_empty_tables(settings):
    listing = anyio.run(_provider(settings).listing)
    assert "lab_sample (0) [BO'SH]" in listing
    assert listing.count("\n") >= 60


def test_live_fallback_without_schema_file(tmp_path):
    settings = Settings(schema_file=str(tmp_path / "yoq.json"), db_password="x")

    class FakeDb(DbClient):
        async def introspect_catalog(self):
            from lims_chatbot.app.schema_catalog import SchemaCatalog, Table, Column
            return SchemaCatalog(tables={"sample": Table(name="sample", rows=None,
                columns=[Column(name="id", type="uuid"), Column(name="sample_no", type="varchar")])})

    provider = SchemaProvider(settings, FakeDb(settings))
    bundle = anyio.run(provider.bundle, "namunalar", ["sample"])
    assert bundle.source == "live-introspection"
    assert "CREATE TABLE sample" in bundle.text


def test_database_switch_does_not_copy_old_sample_values(settings):
    from lims_chatbot.app.schema_catalog import Column, SchemaCatalog, Table

    class NewDb:
        async def introspect_catalog(self):
            return SchemaCatalog(tables={"tnb_analysis": Table("tnb_analysis", None, [
                Column("status", "varchar"), Column("new_result", "numeric"),
            ])})

    settings.schema_refresh_seconds = 600
    settings.db_name = "new_database"
    provider = SchemaProvider(settings, NewDb())
    catalog = anyio.run(provider.catalog)
    assert catalog.table("tnb_analysis").column("status").values is None
    assert catalog.table("tnb_analysis").column("new_result") is not None
    assert catalog.table("instrument") is None
    assert provider.live_verified and provider.source == "live-metadata"


def test_database_switch_requires_live_schema_when_connection_fails(settings):
    class UnavailableDb:
        calls = 0

        async def introspect_catalog(self):
            self.calls += 1
            raise ConnectionError("authentication failed")

    settings.schema_refresh_seconds = 600
    settings.db_name = "new_database"
    db = UnavailableDb()
    provider = SchemaProvider(settings, db)

    async def check():
        for _ in range(2):
            with pytest.raises(RuntimeError, match="Joriy baza sxemasi"):
                await provider.catalog()

    anyio.run(check)
    assert db.calls == 1  # retry backoff still applies to a rejected snapshot
    assert not provider.live_verified and provider.source == ""


def test_same_database_keeps_sample_hints(settings):
    import json
    from pathlib import Path
    from lims_chatbot.app.schema_catalog import Column, SchemaCatalog, Table

    path = Path(settings.schema_file)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["source"] = settings.db_source
    path.write_text(json.dumps(data), encoding="utf-8")

    class LiveDb:
        async def introspect_catalog(self):
            return SchemaCatalog(tables={"tnb_analysis": Table("tnb_analysis", None, [
                Column("status", "varchar"),
            ])})

    settings.schema_refresh_seconds = 600
    provider = SchemaProvider(settings, LiveDb())
    column = anyio.run(provider.catalog).table("tnb_analysis").column("status")
    assert column.values == [["Norma", 2996], ["Chetlanish", 1472]]
    assert column.allowed is None and not column.values_complete
