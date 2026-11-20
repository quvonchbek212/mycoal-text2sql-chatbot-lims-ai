"""Tekshirilgan SQL katalogi testlari.

Katalogdagi SQL modelga NAMUNA sifatida ko'rsatiladi — xato misol modelni
xatoga o'rgatadi. Shuning uchun har bir yozuv:
  * sql_guard dan o'tishi (faqat o'qish);
  * haqiqiy sxema (schema.json) bo'yicha tekshiruvdan xatosiz o'tishi;
  * `tables` maydoni SQL dagi jadvallarga mos bo'lishi;
  * baza ulangan bo'lsa — bazada bajarilishi shart.
"""
import pytest

from lims_chatbot.app.config import get_settings
from lims_chatbot.app.db_client import DbClient
from lims_chatbot.app.schema_catalog import SchemaCatalog
from lims_chatbot.app.sql_catalog import CATALOG, entries_for, find_match, normalize, similar
from lims_chatbot.app.sql_guard import sanitize_select
from lims_chatbot.app.sql_validator import tables_in, validate
from lims_chatbot.tests.conftest import REAL_SCHEMA

ACTIVE_CATALOG = entries_for(SchemaCatalog.load(REAL_SCHEMA)) if REAL_SCHEMA.is_file() else CATALOG


@pytest.mark.parametrize("entry", CATALOG, ids=lambda e: e.question[:40])
def test_entry_is_safe_select(entry):
    assert sanitize_select(entry.sql, 10)


@pytest.mark.parametrize("entry", ACTIVE_CATALOG, ids=lambda e: e.question[:40])
def test_entry_matches_real_schema(entry, real_catalog):
    assert validate(entry.sql, real_catalog) == []


@pytest.mark.parametrize("entry", CATALOG, ids=lambda e: e.question[:40])
def test_entry_tables_declared(entry):
    assert set(tables_in(entry.sql)) == set(entry.tables)


def test_questions_unique():
    qs = [normalize(e.question) for e in CATALOG]
    assert len(qs) == len(set(qs))


def test_fast_path_matches():
    assert find_match("Kalibrovka muddati o‘tgan asboblar qaysilar?") is not None
    assert find_match("Bugun nechta tahlil bo'ldi?") is not None
    assert find_match("Ochiq nomuvofiqliklar") is not None
    assert find_match("Shu oy sexlar bo'yicha tahlillar va chetlanishlar soni") is not None  # Swagger namunasi
    assert find_match("Shu oy sexlar bo‘yicha chetlanishlar soni") is not None


def test_fast_path_does_not_overmatch():
    assert find_match("Kalibrovka qachon qilinadi?") is None
    assert find_match("Kecha nechta tahlil bo'ldi?") is None
    assert find_match("O'tgan oy sexlar bo'yicha tahlillar soni") is None


def test_similar_finds_related_examples():
    top = similar("Qaysi sexda chetlanishlar ko'p?", 3)
    assert top and any("tnb_analysis" in e.tables for e in top)


@pytest.fixture(scope="module")
def live_db():
    settings = get_settings()
    settings = settings.model_copy(update={"schema_refresh_seconds": 600, "sql_row_limit": 5})
    db = DbClient(settings)
    try:
        db._ping_sync()
    except Exception:  # noqa: BLE001
        pytest.skip("Baza ulanmagan (VPN/LAN) — katalog SQL lari bazada bajarilmadi")
    return db


@pytest.mark.parametrize("entry", ACTIVE_CATALOG, ids=lambda e: e.question[:40])
def test_entry_executes_on_database(entry, live_db):
    # Exercise the production adapter, including schema-qualified tables and the
    # pg_catalog-only function search path. Each query owns its transaction.
    live_db._run_select_sync(entry.sql)
