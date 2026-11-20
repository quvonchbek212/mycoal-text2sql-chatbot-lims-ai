"""Chatbot aniqligini o'lchash — baholash to'plamini (eval_set.py) TO'LIQ quvurdan o'tkazadi.

Ishga tushirish (loyiha ildizidan; baza va LLM ulangan bo'lishi kerak):
    python -m lims_chatbot.tools.evaluate
    python -m lims_chatbot.tools.evaluate --only 3,7 --out hisobot.json
    python -m lims_chatbot.tools.evaluate --lang ru      # javob rus tilida (SQL aniqligi o'zgarmasligi kerak)

Har savol uchun: yo'nalish to'g'rimi, bot natijasi oltin SQL natijasiga mosmi,
qancha vaqt ketdi. Har o'zgarishdan keyin ishga tushiring — aniqlik raqamda
ko'rinadi ("yaxshilandi" degan taxmin emas).
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import asyncio
import json
import pathlib
import sys
import time
from typing import Any

import psycopg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from lims_chatbot.app.config import get_settings  # noqa: E402
from lims_chatbot.app.db_client import DbClient, jsonable  # noqa: E402
from lims_chatbot.app.graph import AssistantGraph  # noqa: E402
from lims_chatbot.app.llm import LlmClient  # noqa: E402
from lims_chatbot.app.schema_provider import SchemaProvider  # noqa: E402
from lims_chatbot.app.sql_service import SqlService  # noqa: E402
from lims_chatbot.tools.eval_set import EVAL_SET  # noqa: E402


def norm(v: Any) -> str:
    v = jsonable(v)
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, (int, float)):
        return f"{float(v):.4f}".rstrip("0").rstrip(".")
    s = str(v).strip()
    try:
        return f"{float(s):.4f}".rstrip("0").rstrip(".")
    except ValueError:
        return s


def compare(mode: str, gold: list[tuple], bot_rows: list[dict], bot_count: int,
            bot_total: int | None = None) -> tuple[bool, str]:
    """bot_total — natija kesilgan bo'lsa jami son (ro'yxat 20 ta ko'rsatiladi, jami alohida)."""
    bot = [[norm(v) for v in (r.values() if isinstance(r, dict) else [r])] for r in bot_rows]
    gold_n = [[norm(v) for v in row] for row in gold]
    size = bot_total if bot_total is not None else len(bot)
    if mode == "scalar":
        ok = len(gold_n) == len(bot) == 1 and len(gold_n[0]) == len(bot[0]) == 1 and bot[0][0] == gold_n[0][0]
        return ok, "" if ok else f"scalar mos emas: expected={gold_n}, actual={bot}"
    if mode == "top1":
        ok = bool(bot and gold_n) and bot[0][0] == gold_n[0][0]
        return ok, "" if ok else "Birinchi satr mos emas"
    if mode == "first_column_set":
        expected = Counter(r[0] for r in gold_n)
        actual = Counter(r[0] for r in bot if r)
    elif mode in ("overlap80", "rows_subset"):
        expected = Counter(tuple(r) for r in gold_n)
        width = len(gold_n[0]) if gold_n else 0
        bot_width = len(bot[0]) if bot else 0
        # Extra explanatory columns are allowed. The same ordered column mapping
        # must match complete expected tuples for every displayed row.
        mappings = combinations(range(min(bot_width, 32)), width) if width else [()]
        actuals = [Counter(tuple(row[i] for i in indices) for row in bot)
                   for indices in mappings if all(len(row) == bot_width for row in bot)]
        actual = next((a for a in actuals if not (a - expected)), Counter(tuple(r) for r in bot))
    else:
        raise ValueError(mode)
    if mode == "overlap80":
        hits = sum((actual & expected).values())
        ok = not (actual - expected) and len(bot) == len(gold_n) and hits >= 0.8 * len(gold_n)
        return ok, f"To'liq satr mosligi {hits}/{len(gold_n)}"
    if bot_total is not None:
        ok = bool(actual or not expected) and not (actual - expected) and size == len(gold_n)
        return ok, "Faqat ko'rsatilgan satrlar va jami son tekshirildi" if ok else "Kesilgan natija mos emas"
    ok = actual == expected
    return ok, "" if ok else "Natija qiymatlari yoki takrorlanish soni mos emas"


async def main_async(only: set[int] | None, out: str | None, lang: str = "uz") -> int:
    settings = get_settings()
    llm, db = LlmClient(settings), DbClient(settings)
    provider = SchemaProvider(settings, db)
    graph = AssistantGraph(settings, llm, SqlService(settings, llm, db, provider), provider)

    try:
        catalog = await provider.catalog()
    except Exception as exc:
        await llm.close()
        print(f"Sxema tekshiruvi ishlamadi: {type(exc).__name__}")
        return 1
    if catalog.profile.name == "coal":
        from lims_chatbot.tools.coal_eval_set import EVAL_SET as eval_set
    elif catalog.profile.name == "tnb":
        eval_set = EVAL_SET
    else:
        await llm.close()
        print("Bu sxema uchun baholash to'plami hali belgilanmagan")
        return 1
    print(f"Baholash profili: {catalog.profile.name}", flush=True)

    report: list[dict[str, Any]] = []
    # autocommit: LLM javobini kutish paytida ochiq tranzaksiya qolmasin
    # (idle_in_transaction_session_timeout ulanishni uzadi).
    with psycopg.connect(**db.conn_kwargs(), autocommit=True) as conn:
        for i, item in enumerate(eval_set, start=1):
            if only and i not in only:
                continue
            history: list[dict[str, Any]] = []
            for hq in item.get("history", []):
                st = await graph.run(hq, history, lang)
                if st.get("sql"):
                    history.append({"question": hq, "sql": st["sql"]})

            t0 = time.monotonic()
            state = await graph.run(item["q"], history, lang)
            elapsed = time.monotonic() - t0

            expected = item.get("route", "database")
            ok, note = state.get("route") == expected, ""
            if not ok:
                note = f"yo'nalish {state.get('route')} (kutilgan {expected})"
            elif expected == "database":
                if state.get("error") or not state.get("sql"):
                    ok, note = False, f"xato: {state.get('error') or state.get('answer', '')[:120]}"
                else:
                    results = []
                    for g in item["gold"]:
                        g_sql, mode = g if isinstance(g, tuple) else (g, item.get("compare", "scalar"))
                        with conn.cursor() as cur:
                            cur.execute(db._checked_sync(g_sql))
                            total = state.get("total_count") if state.get("truncated") else None
                            results.append(compare(mode, cur.fetchall(), state.get("rows", []),
                                                   state.get("row_count", 0), total))
                    ok = any(r[0] for r in results)
                    note = next((r[1] for r in results if r[0]), results[0][1])

            row = {
                "n": i, "q": item["q"], "ok": ok, "route": state.get("route"), "sec": round(elapsed, 1),
                "fast": state.get("fast_path", False), "sql": state.get("sql"),
                "answer": (state.get("answer") or "")[:200], "note": note,
                "timings": state.get("timings", {}),
            }
            report.append(row)
            mark = "✅" if ok else "❌"
            stages = " ".join(f"{k}={v:.0f}" for k, v in row["timings"].items())
            print(f"{mark} {i:2}. {elapsed:5.1f}s {'⚡' if row['fast'] else ' '} {item['q'][:55]:55} [{stages}]"
                  + (f"\n        → {note}" if not ok else ""), flush=True)

    await llm.close()
    passed = sum(r["ok"] for r in report)
    secs = [r["sec"] for r in report]
    print(f"\nNATIJA: {passed}/{len(report)} to'g'ri ({100 * passed / max(len(report), 1):.0f}%) | "
          f"o'rtacha {sum(secs) / max(len(secs), 1):.1f}s, eng uzuni {max(secs, default=0):.1f}s")
    if out:
        pathlib.Path(out).write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"Hisobot: {out}")
    return 0 if passed == len(report) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="LIMS chatbot aniqligini o'lchash")
    parser.add_argument("--only", help="Faqat shu raqamli savollar (masalan 1,5,7)")
    parser.add_argument("--out", help="JSON hisobot fayli")
    parser.add_argument("--lang", default="uz", choices=["uz", "ru", "en"], help="Javob tili")
    args = parser.parse_args()
    only = {int(x) for x in args.only.split(",")} if args.only else None
    return asyncio.run(main_async(only, args.out, args.lang))


if __name__ == "__main__":
    raise SystemExit(main())
