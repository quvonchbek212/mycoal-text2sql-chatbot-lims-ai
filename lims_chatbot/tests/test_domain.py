"""Domen izohlari bazaga mosligini tekshiradi.

Izoh ham promptga tushadi: unda mavjud bo'lmagan jadval/ustun nomi bo'lsa,
model uni haqiqiy deb qabul qiladi va so'rov bazada yiqiladi.
"""
import pathlib
import re

from lims_chatbot.app import domain

_TABLE_REF = re.compile(r"\b((?:tnb_|status_|core_|instrument_|reagent_|test_|sampling_)[a-z_]+)\b")
_COL_REF = re.compile(r"\b([a-z][a-z_]+)\.([a-z_]+)\b")


def test_notes_reference_existing_tables(real_catalog):
    for table in real_catalog.profile.table_notes:
        assert table in real_catalog.tables, table


def test_column_notes_reference_existing_columns(real_catalog):
    for key in real_catalog.profile.column_notes:
        table, column = key.split(".", 1)
        assert real_catalog.table(table) is not None, key
        assert real_catalog.table(table).column(column) is not None, key


def test_logical_fks_exist(real_catalog):
    for table in real_catalog.tables.values():
        for fk in table.fks:
            if fk.get("logical"):
                assert real_catalog.profile.name == "tnb"
                assert table.column(fk["column"]) is not None
                assert real_catalog.table(fk["ref_table"]).column(fk["ref_column"]) is not None


def test_synonym_targets_exist(real_catalog):
    for term, tables in real_catalog.profile.synonyms.items():
        for t in tables:
            assert t in real_catalog.tables, (term, t)


def test_text_mentions_are_real(real_catalog):
    """Izoh/qoida/lug'at matnidagi `jadval` va `jadval.ustun` havolalari bazada bor."""
    profile = real_catalog.profile
    texts = [profile.rules, profile.glossary, *profile.table_notes.values()]
    for text in texts:
        for name in _TABLE_REF.findall(text):
            is_column = any(t.column(name) is not None for t in real_catalog.tables.values())
            assert name in real_catalog.tables or is_column, name
        for table, column in _COL_REF.findall(text):
            t = real_catalog.table(table)
            if t is not None:  # "sd.code" kabi taxalluslar tekshirilmaydi
                assert t.column(column) is not None, f"{table}.{column}"


def test_excluded_tables_not_in_schema(real_catalog):
    for t in domain.EXCLUDED_TABLES:
        assert t not in real_catalog.tables


def test_ddl_sql_is_up_to_date(real_catalog):
    """ddl.sql = schema.json + domain.py izohlari. Izoh o'zgargach fayl yangilanmasa, test yiqiladi:
    python -m lims_chatbot.tools.generate_ddl --render-only
    """
    ddl_file = pathlib.Path(__file__).resolve().parents[1] / "schema" / "ddl.sql"
    ddl = ddl_file.read_text(encoding="utf-8")
    body = ddl[ddl.index("-- TABLE: "):].strip()
    assert body == real_catalog.render_full().strip(), (
        "ddl.sql eskirgan — yangilang: python -m lims_chatbot.tools.generate_ddl --render-only"
    )
