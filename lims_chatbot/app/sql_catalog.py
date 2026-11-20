"""Tekshirilgan SQL katalogi — chatbot "bilib turgan" savollar.

Ikki vazifa:
  1. MISOL — savolga eng o'xshash 3 ta yozuv SQL promptiga namuna sifatida
     qo'shiladi. Model jadval/ustun/JOIN yo'lini shulardan ko'chiradi — bu
     aniqlikni eng ko'p oshiradigan narsa.
  2. TEZ YO'L (`match`) — savol shablonga ANIQ mos kelsa, SQL LLM'siz shu
     yerdan olinadi (tezroq va xatosiz). `match` faqat bir ma'noli
     iboralarga yoziladi; shubha bo'lsa bo'sh qoldiriladi.

QAT'IY QOIDA: har bir `sql` haqiqiy bazada bajarilib tekshirilgan.
`tests/test_sql_catalog.py` ularni sxema bo'yicha (bazasiz) va baza
ulanganda bajarib ham tekshiradi — sxema o'zgarsa test yiqiladi.

Yangi yozuv qo'shish: SQL ni avval bazada ishlating, keyin shu yerga qo'shing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_APOSTROPHES = re.compile(r"[‘’`ʻʼ']")
_WORD = re.compile(r"[a-zа-яёўқғҳ0-9']+", re.IGNORECASE)
_STOP = {
    "va", "bilan", "uchun", "bo'yicha", "qancha", "nechta", "qaysi", "ko'rsat", "ber",
    "menga", "bor", "ham", "the", "ro'yxati", "ro'yxatini", "soni", "sonini", "necha",
}


def normalize(text: str) -> str:
    """Kichik harf, apostrof variantlari → ' (o‘tgan, o`tgan → o'tgan)."""
    return _APOSTROPHES.sub("'", (text or "").lower()).strip()


def _stem(word: str) -> str:
    # O'zbekcha qo'shimchalarni qisqartirish uchun oddiy kesish (tahlillar → tahlil).
    return word[:6] if len(word) > 6 else word


def tokens(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(normalize(text)) if w not in _STOP and len(w) > 2}


@dataclass(frozen=True)
class CatalogEntry:
    question: str
    sql: str
    tables: tuple[str, ...]
    match: str = ""  # normalize() qilingan savolga qo'llanadigan regex (tez yo'l)

    def matches(self, question: str) -> bool:
        q = normalize(question).rstrip("?!. ")
        if q == normalize(self.question).rstrip("?!. "):
            return True
        return bool(self.match) and re.fullmatch(self.match, q) is not None


CATALOG: list[CatalogEntry] = [
    # ============================ TNB tahlillar ============================
    CatalogEntry(
        "Bugun nechta tahlil o'tkazildi va ulardan nechtasida chetlanish bor?",
        """SELECT count(*) AS tahlillar_soni,
       count(*) FILTER (WHERE a.status = 'Chetlanish') AS chetlanishlar_soni
FROM tnb_analysis a
WHERE a.analysis_date = CURRENT_DATE AND a.archived_at IS NULL""",
        ("tnb_analysis",),
        match=r"bugun(gi)? (nechta|qancha) tahlil(?:lar)?(?: (?:bo'ldi|o'tkazildi))?",
    ),
    CatalogEntry(
        "Oxirgi 7 kunda nechta chetlanish aniqlandi?",
        """SELECT count(*) AS chetlanishlar_soni
FROM tnb_analysis a
WHERE a.status = 'Chetlanish' AND a.archived_at IS NULL
  AND a.analysis_date >= CURRENT_DATE - 6""",
        ("tnb_analysis",),
    ),
    CatalogEntry(
        "Shu oy sexlar bo'yicha tahlillar soni va chetlanishlar",
        """SELECT g.name AS sex,
       count(*) AS tahlillar_soni,
       count(*) FILTER (WHERE a.status = 'Chetlanish') AS chetlanishlar_soni
FROM tnb_analysis a
JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code
JOIN tnb_sampling_point_group g ON g.id = sp.group_id
WHERE a.archived_at IS NULL
  AND a.analysis_date >= date_trunc('month', CURRENT_DATE)
GROUP BY g.name
ORDER BY tahlillar_soni DESC""",
        ("tnb_analysis", "tnb_sampling_point", "tnb_sampling_point_group"),
        match=r"shu oy(dagi)? sexlar bo'yicha (?:tahlillar(?: soni)?(?: va chetlanishlar)?(?: soni)?|chetlanishlar soni)",
    ),
    CatalogEntry(
        "Qaysi nazorat nuqtalarida eng ko'p chetlanish bo'lgan? (top 10)",
        """SELECT sp.code AS nuqta_kodi, sp.name AS nazorat_nuqtasi, g.name AS sex,
       count(*) AS chetlanishlar_soni
FROM tnb_analysis a
JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code
LEFT JOIN tnb_sampling_point_group g ON g.id = sp.group_id
WHERE a.status = 'Chetlanish' AND a.archived_at IS NULL
GROUP BY sp.code, sp.name, g.name
ORDER BY chetlanishlar_soni DESC
LIMIT 10""",
        ("tnb_analysis", "tnb_sampling_point", "tnb_sampling_point_group"),
    ),
    CatalogEntry(
        "Oxirgi 30 kunda kunlik tahlillar soni (dinamika)",
        """SELECT a.analysis_date AS sana,
       count(*) AS tahlillar_soni,
       count(*) FILTER (WHERE a.status = 'Chetlanish') AS chetlanishlar_soni
FROM tnb_analysis a
WHERE a.archived_at IS NULL AND a.analysis_date >= CURRENT_DATE - 29
GROUP BY a.analysis_date
ORDER BY a.analysis_date""",
        ("tnb_analysis",),
    ),
    CatalogEntry(
        "Ammiak ishlab chiqarish sexidagi oxirgi 20 ta tahlil",
        """SELECT a.analysis_date AS sana, a.analysis_time AS vaqt, sp.name AS nazorat_nuqtasi,
       a.status AS natija, a.analyst_full_name AS tahlilchi
FROM tnb_analysis a
JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code
JOIN tnb_sampling_point_group g ON g.id = sp.group_id
WHERE a.archived_at IS NULL
  AND (g.name ILIKE '%ammiak%' OR g.name ILIKE '%аммиак%')
ORDER BY a.analysis_date DESC, a.analysis_time DESC
LIMIT 20""",
        ("tnb_analysis", "tnb_sampling_point", "tnb_sampling_point_group"),
    ),
    CatalogEntry(
        "Sexlar bo'yicha chetlanish ulushi (foizda)",
        """SELECT g.name AS sex,
       count(*) AS tahlillar_soni,
       round(100.0 * count(*) FILTER (WHERE a.status = 'Chetlanish') / count(*), 1) AS chetlanish_foizi
FROM tnb_analysis a
JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code
JOIN tnb_sampling_point_group g ON g.id = sp.group_id
WHERE a.archived_at IS NULL
GROUP BY g.name
HAVING count(*) >= 10
ORDER BY chetlanish_foizi DESC""",
        ("tnb_analysis", "tnb_sampling_point", "tnb_sampling_point_group"),
    ),
    CatalogEntry(
        # Naqsh: guruhlash uchun qo'shilgan ma'lumotnoma (lab) ga is_active/archived_at
        # filtri QO'YILMAYDI — nofaol laboratoriyaning tahlillari ham hisobda qolsin.
        "Laboratoriyalar bo'yicha TNB tahlillari soni",
        """SELECT l.name AS laboratoriya, count(*) AS tahlillar_soni
FROM tnb_analysis a
JOIN lab l ON l.id = a.lab_id
WHERE a.archived_at IS NULL
GROUP BY l.id, l.name
ORDER BY tahlillar_soni DESC""",
        ("tnb_analysis", "lab"),
    ),
    CatalogEntry(
        "Eng ko'p tahlil o'tkazgan tahlilchilar (shu oy)",
        """SELECT a.analyst_full_name AS tahlilchi, count(*) AS tahlillar_soni
FROM tnb_analysis a
WHERE a.archived_at IS NULL AND a.analysis_date >= date_trunc('month', CURRENT_DATE)
GROUP BY a.analyst_full_name
ORDER BY tahlillar_soni DESC
LIMIT 10""",
        ("tnb_analysis",),
    ),
    # ============================ TNB ma'lumotnomalar ============================
    CatalogEntry(
        "Sexlar bo'yicha faol nazorat nuqtalari soni",
        """SELECT g.name AS sex, count(*) AS nuqtalar_soni
FROM tnb_sampling_point sp
JOIN tnb_sampling_point_group g ON g.id = sp.group_id
WHERE sp.is_active
GROUP BY g.name
ORDER BY nuqtalar_soni DESC""",
        ("tnb_sampling_point", "tnb_sampling_point_group"),
    ),
    CatalogEntry(
        "Metodikalar holati bo'yicha soni (tayyor / qoralama)",
        """SELECT m.status AS holat, count(*) AS metodikalar_soni
FROM tnb_methodika m
WHERE m.is_active
GROUP BY m.status
ORDER BY metodikalar_soni DESC""",
        ("tnb_methodika",),
    ),
    CatalogEntry(
        "Ammiak bo'yicha metodikalar ro'yxati",
        """SELECT m.code AS kod, m.name AS metodika, m.status AS holat
FROM tnb_methodika m
WHERE m.is_active AND (m.name ILIKE '%ammiak%' OR m.name ILIKE '%аммиак%')
ORDER BY m.code
LIMIT 20""",
        ("tnb_methodika",),
    ),
    CatalogEntry(
        "Smenalar ro'yxati va vaqtlari",
        """SELECT s.name AS smena, s.start_time AS boshlanishi, s.end_time AS tugashi
FROM tnb_lab_shift s
WHERE s.is_active
ORDER BY s.sort_order""",
        ("tnb_lab_shift",),
    ),
    # ============================ Partiya / sertifikat ============================
    CatalogEntry(
        "Partiyalar holati bo'yicha soni",
        """SELECT p.status AS holat, count(*) AS partiyalar_soni
FROM tnb_party p
WHERE p.archived_at IS NULL
GROUP BY p.status
ORDER BY partiyalar_soni DESC""",
        ("tnb_party",),
    ),
    CatalogEntry(
        "Tahlil kutilayotgan partiyalar ro'yxati",
        """SELECT p.party_no AS partiya_raqami, p.product_name AS mahsulot, p.shift_date AS smena_sanasi,
       p.shift_type AS smena
FROM tnb_party p
WHERE p.archived_at IS NULL AND p.status = 'Tahlil kutilmoqda'
ORDER BY p.shift_date DESC""",
        ("tnb_party",),
    ),
    CatalogEntry(
        "Shu oy nechta sifat sertifikati berildi (turi bo'yicha)?",
        """SELECT c.type AS turi, count(*) AS sertifikatlar_soni
FROM tnb_certificate c
WHERE c.status = 'ISSUED' AND c.archived_at IS NULL
  AND c.issue_date >= date_trunc('month', CURRENT_DATE)
GROUP BY c.type""",
        ("tnb_certificate",),
    ),
    CatalogEntry(
        "Bekor qilingan sertifikatlar",
        """SELECT c.certificate_no AS sertifikat_raqami, c.issue_date AS berilgan_sana,
       c.cancelled_at AS bekor_qilingan, c.cancellation_reason AS sabab
FROM tnb_certificate c
WHERE c.status = 'CANCELLED'
ORDER BY c.cancelled_at DESC NULLS LAST""",
        ("tnb_certificate",),
    ),
    CatalogEntry(
        "Kiruvchi xomashyo nazorati holati",
        """SELECT ic.task_no AS topshiriq, ic.supplier AS yetkazib_beruvchi, ic.quantity_tons AS miqdor_tonna,
       ic.arrived_at AS kelgan_vaqt, ic.status AS holat
FROM tnb_incoming_control ic
WHERE ic.archived_at IS NULL
ORDER BY ic.arrived_at DESC""",
        ("tnb_incoming_control",),
    ),
    # ============================ Asbob / reagent ============================
    CatalogEntry(
        "Kalibrovka muddati o'tgan asboblar",
        """SELECT i.code AS kod, i.name AS asbob, l.name AS laboratoriya, i.calibration_due_at AS kalibrovka_muddati
FROM instrument i
LEFT JOIN lab l ON l.id = i.lab_id
WHERE i.archived_at IS NULL AND i.calibration_due_at < now()
ORDER BY i.calibration_due_at""",
        ("instrument", "lab"),
        match=r"kalibrovka(si)? muddati o'tgan asboblar(?: qaysilar| ro'yxati)?",
    ),
    CatalogEntry(
        "Keyingi 30 kunda kalibrovka muddati tugaydigan asboblar",
        """SELECT i.code AS kod, i.name AS asbob, i.calibration_due_at AS kalibrovka_muddati
FROM instrument i
WHERE i.archived_at IS NULL
  AND i.calibration_due_at >= now() AND i.calibration_due_at < now() + interval '30 days'
ORDER BY i.calibration_due_at""",
        ("instrument",),
    ),
    CatalogEntry(
        "Asboblar holati bo'yicha soni",
        """SELECT sd.code AS holat_kodi, sd.label AS holat, count(*) AS asboblar_soni
FROM instrument i
JOIN status_dictionary sd ON sd.id = i.status_id
WHERE i.archived_at IS NULL
GROUP BY sd.code, sd.label
ORDER BY asboblar_soni DESC""",
        ("instrument", "status_dictionary"),
    ),
    CatalogEntry(
        "Yaroqlilik muddati o'tgan reagent partiyalari",
        """SELECT r.name AS reagent, rl.lot_no AS partiya, rl.expires_at AS yaroqlilik_muddati,
       rl.available_quantity AS qoldiq
FROM reagent_lot rl
JOIN reagent r ON r.id = rl.reagent_id
WHERE rl.archived_at IS NULL AND rl.expires_at < now()
ORDER BY rl.expires_at""",
        ("reagent_lot", "reagent"),
        match=r"(muddati o'tgan|eskirgan) reagent(?:lar| partiyalari)(?: ro'yxati)?",
    ),
    CatalogEntry(
        "Reagent partiyalari holati bo'yicha",
        """SELECT sd.code AS holat_kodi, sd.label AS holat, count(*) AS partiyalar_soni
FROM reagent_lot rl
JOIN status_dictionary sd ON sd.id = rl.status_id
WHERE rl.archived_at IS NULL
GROUP BY sd.code, sd.label
ORDER BY partiyalar_soni DESC""",
        ("reagent_lot", "status_dictionary"),
    ),
    # ============================ Sifat: NC / CAPA / OOS ============================
    CatalogEntry(
        "Ochiq nomuvofiqliklar ro'yxati",
        """SELECT nc.nc_no AS raqam, nc.title AS nomi, nc.severity_code AS jiddiylik,
       nc.identified_at AS aniqlangan, nc.due_at AS muddat
FROM non_conformance nc
JOIN status_dictionary sd ON sd.id = nc.status_id
WHERE nc.archived_at IS NULL AND sd.code = 'NC_OPEN'
ORDER BY nc.identified_at DESC""",
        ("non_conformance", "status_dictionary"),
        match=r"ochiq (nomuvofiqliklar|nc)(?: ro'yxati)?",
    ),
    CatalogEntry(
        "Muddati o'tgan, bajarilmagan CAPA choralari",
        """SELECT ca.action_no AS raqam, ca.title AS chora, ca.due_at AS muddat, sd.label AS holat
FROM capa_action ca
JOIN status_dictionary sd ON sd.id = ca.status_id
WHERE ca.archived_at IS NULL AND ca.completed_at IS NULL AND ca.due_at < now()
ORDER BY ca.due_at""",
        ("capa_action", "status_dictionary"),
    ),
    CatalogEntry(
        "Me'yordan tashqari (OOS) test natijalari",
        """SELECT s.sample_no AS namuna, td.name AS test, r.numeric_value AS qiymat, r.evaluation_code AS baho,
       r.submitted_at AS kiritilgan
FROM result r
JOIN test_order t ON t.id = r.test_order_id
JOIN sample s ON s.id = t.sample_id
LEFT JOIN test_definition td ON td.id = t.test_definition_id
WHERE r.archived_at IS NULL AND (r.is_out_of_spec OR r.evaluation_code = 'OOS')
ORDER BY r.submitted_at DESC""",
        ("result", "test_order", "sample", "test_definition"),
    ),
    CatalogEntry(
        "LIMS namunalari holati bo'yicha soni",
        """SELECT sd.code AS holat_kodi, sd.label AS holat, count(*) AS namunalar_soni
FROM sample s
JOIN status_dictionary sd ON sd.id = s.status_id
WHERE s.archived_at IS NULL
GROUP BY sd.code, sd.label
ORDER BY namunalar_soni DESC""",
        ("sample", "status_dictionary"),
    ),
    CatalogEntry(
        "Muddati o'tgan namuna olish topshiriqlari",
        """SELECT t.task_no AS topshiriq, p.name AS nuqta, t.planned_at AS rejalashtirilgan, t.due_at AS muddat,
       t.status AS holat
FROM sampling_task t
LEFT JOIN sampling_point p ON p.id = t.sampling_point_id
WHERE t.is_overdue OR t.status = 'OVERDUE'
ORDER BY t.due_at""",
        ("sampling_task", "sampling_point"),
    ),
    # ============================ Ma'lumotnomalar ============================
    CatalogEntry(
        "Faol foydalanuvchilar soni rollar bo'yicha",
        """SELECT u.role AS rol, count(*) AS foydalanuvchilar_soni
FROM core_user u
WHERE u.is_active AND u.archived_at IS NULL
GROUP BY u.role
ORDER BY foydalanuvchilar_soni DESC""",
        ("core_user",),
    ),
    CatalogEntry(
        "Faol laboratoriyalar soni",
        """SELECT count(*) AS laboratoriyalar_soni
FROM lab l
WHERE l.is_active AND l.archived_at IS NULL
""",
        ("lab",),
    ),
    CatalogEntry(
        "Faol mahsulotlar ro'yxati",
        """SELECT p.code AS kod, p.name AS mahsulot
FROM product p
WHERE p.is_active AND p.archived_at IS NULL
ORDER BY p.name""",
        ("product",),
    ),
]


def entries_for(catalog=None) -> list[CatalogEntry]:
    if catalog is None:
        return CATALOG
    from .sql_validator import validate

    if catalog.profile.name == "tnb":
        candidates = CATALOG
    else:
        candidates = [e for e in CATALOG if not any(t.startswith("tnb_") for t in e.tables)]
        if catalog.profile.name == "coal":
            from .coal_sql_catalog import CATALOG as coal_entries
            candidates = coal_entries + candidates
    return [entry for entry in candidates if not validate(entry.sql, catalog)]


def find_match(question: str, catalog=None) -> CatalogEntry | None:
    for entry in entries_for(catalog):
        if entry.matches(question):
            return entry
    return None


def similar(question: str, k: int = 3, catalog=None) -> list[CatalogEntry]:
    """Savolga so'zlari eng ko'p mos keladigan k ta yozuv (Jaccard o'xshashligi)."""
    q = tokens(question)
    if not q or k <= 0:
        return []
    scored = []
    for entry in entries_for(catalog):
        e = tokens(entry.question)
        inter = len(q & e)
        if inter:
            scored.append((inter / len(q | e), entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:k]]
