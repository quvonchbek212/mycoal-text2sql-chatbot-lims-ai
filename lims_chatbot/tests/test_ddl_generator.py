"""DDL generatori va chizuvchi testlari — bazasiz."""
import re

import sqlglot

from lims_chatbot.app.schema_catalog import quote_ident, short_type
from lims_chatbot.tools.generate_ddl import compact_check, parse_enum_check, wants_values


# ---------------- CHECK tahlili ----------------
def test_parse_enum_check_varchar():
    d = ("CHECK (((status)::text = ANY ((ARRAY['DRAFT'::character varying, "
         "'READY'::character varying])::text[])))")
    assert parse_enum_check(d) == ("status", ["DRAFT", "READY"])


def test_parse_enum_check_quoted_column():
    d = ("CHECK (((\"analysisStatus\")::text = ANY ((ARRAY['PENDING'::character varying, "
         "'PASSED'::character varying])::text[])))")
    assert parse_enum_check(d) == ("analysisStatus", ["PENDING", "PASSED"])


def test_parse_enum_check_ignores_other_checks():
    assert parse_enum_check("CHECK ((interval_count >= 1))") is None


def test_compact_check():
    assert compact_check("CHECK ((interval_count >= 1))") == "interval_count >= 1"


# ---------------- qaysi ustun qiymatlari yig'iladi ----------------
def test_wants_values_status_like_columns():
    for name in ("status", "priority_level", "measurement_unit", "event_code", "lab_type", "analysisStatus"):
        assert wants_values(name), name


def test_wants_values_skips_ids_and_private_text():
    for name in ("sample_type_id", "priority_id", "id", "model", "full_name", "analyst_full_name",
                 "transport_number", "decision_no", "cancellation_reason", "status_reason", "comment",
                 "email", "frequency_raw", "norm"):
        assert not wants_values(name), name


# ---------------- chizish ----------------
def test_short_type():
    assert short_type("character varying(255)") == "varchar"
    assert short_type("timestamp(6) with time zone") == "timestamptz"
    assert short_type("time(6) without time zone") == "time"


def test_quote_ident():
    assert quote_ident("status") == "status"
    assert quote_ident("analysisStatus") == '"analysisStatus"'
    assert quote_ident("group") == '"group"'


def test_render_table_markers(catalog):
    text = catalog.render_table("tnb_analysis")
    assert text.startswith("-- TABLE: tnb_analysis  (satrlar: 4468)")
    assert "BAZADA: 'Norma' 2996, 'Chetlanish' 1472" in text
    assert "oraliq: 2026-06-29 … 2026-09-18" in text
    assert "[katta obyekt (oid)" in text
    assert "[har doim NULL" in text
    assert "mantiqiy bog'lanish" in text


def test_render_status_ref_and_sensitive(catalog):
    assert "JOIN status_dictionary sd" in catalog.render_table("instrument")
    assert "[MAXFIY" in catalog.render_table("core_user")
    assert "BO`SH" in catalog.render_table("lab_sample")


def test_render_enum_unused_values(catalog):
    text = catalog.render_table("tnb_party")
    assert "RUXSAT: 'PENDING', 'PASSED', 'REJECTED'" in text
    assert "ISHLATILMAGAN: REJECTED" in text
    assert '"analysisStatus"' in text


def test_rendered_ddl_is_valid_sql(catalog):
    """Vergullar izoh ichiga tushib qolmasligi kerak — izohsiz DDL parse bo'lishi shart."""
    for name in catalog.tables:
        text = catalog.render_table(name)
        code = "\n".join(re.sub(r"\s+--.*$", "", ln) for ln in text.splitlines() if not ln.startswith("--"))
        code = code.replace("varchar NOT NULL", "text NOT NULL").replace("oid", "integer")
        assert sqlglot.parse_one(code, dialect="postgres") is not None, name
