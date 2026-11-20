"""JSON konvertatsiya va SQL ajratish testlari (tarmoqsiz)."""
import datetime as dt
import decimal
import uuid

from lims_chatbot.app.db_client import MAX_TEXT, jsonable
from lims_chatbot.app.sql_service import extract_sql, history_block


# ---------------- jsonable: /api/chat 500 xatosining oldini oladi ----------------
def test_jsonable_uuid():
    u = uuid.uuid4()
    assert jsonable(u) == str(u)


def test_jsonable_datetime_and_date():
    assert jsonable(dt.datetime(2026, 9, 12, 10, 30)) == "2026-09-12T10:30:00"
    assert jsonable(dt.date(2026, 9, 12)) == "2026-09-12"


def test_jsonable_decimal():
    assert jsonable(decimal.Decimal("12.50")) == 12.5


def test_jsonable_bytes():
    assert "bayt" in jsonable(b"\x00\x01\x02")


def test_jsonable_nested():
    out = jsonable({"a": [decimal.Decimal("1.5"), dt.date(2026, 1, 1)]})
    assert out == {"a": [1.5, "2026-01-01"]}


def test_jsonable_primitives_untouched():
    assert jsonable("matn") == "matn"
    assert jsonable(42) == 42
    assert jsonable(None) is None
    assert jsonable(True) is True


def test_jsonable_long_text_truncated():
    """JSON/izoh ustunlaridagi ulkan matnlar UI va modelni to'ldirib yubormasin."""
    out = jsonable("x" * (MAX_TEXT + 500))
    assert len(out) == MAX_TEXT + 1 and out.endswith("…")


# ---------------- SQL ajratish ----------------
def test_extract_sql_from_fence():
    sql, clarify = extract_sql("Mana:\n```sql\nSELECT 1\n```\nTayyor.")
    assert sql == "SELECT 1" and clarify is None


def test_extract_sql_bare_select():
    sql, clarify = extract_sql("SELECT id FROM sample")
    assert sql and sql.startswith("SELECT") and clarify is None


def test_extract_clarify_question():
    sql, clarify = extract_sql("SAVOL: Qaysi davr uchun kerak?")
    assert sql is None and clarify == "Qaysi davr uchun kerak?"


def test_extract_none_for_plain_text():
    sql, clarify = extract_sql("Bu haqda ma'lumot yo'q.")
    assert sql is None and clarify


# ---------------- suhbat tarixi ----------------
def test_history_block_empty():
    assert history_block(None) == "" and history_block([]) == ""


def test_history_block_keeps_last_four_turns_with_sql():
    hist = [{"question": f"savol {i}", "sql": f"SELECT {i}\n FROM t"} for i in range(6)]
    text = history_block(hist)
    assert "savol 5" in text and "savol 2" in text and "savol 1" not in text
    assert "SELECT 3 FROM t" in text  # bir qatorga yig'iladi
