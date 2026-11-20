"""Coal queries validated against inspected column/FK definitions.

Live execution must also be checked once the database role has SELECT access.
Avoid unverified status codes and measurement units.
"""
from .sql_catalog import CatalogEntry

CATALOG = [
    CatalogEntry(
        "Ish jurnalida nechta alohida ekskavator bor?",
        """SELECT count(DISTINCT excavator_number) AS ish_jurnalidagi_alohida_ekskavatorlar_soni
FROM daily_excavator_work""",
        ("daily_excavator_work",),
        match=(r"(?:ish jurnalida (?:nechta|qancha) (?:(?:alohida|noyob) )?"
               r"ekskav(?:ator|atr)(?:lar)?(?: bor)?|"
               r"ish jurnalidagi (?:(?:alohida|noyob) )?ekskavatorlar soni|"
               r"(?:jami )?ekskav(?:ator|atr)(?:lar)? (?:nechta|qancha)(?: bor)?|"
               r"jami (?:nechta|qancha) ekskav(?:ator|atr)(?:lar)?(?: bor)?|"
               r"jami ekskav(?:ator|atr)(?:lar)? soni)"),
    ),
    CatalogEntry(
        "Bugun nechta ko'mir laboratoriya natijasi qayd etilgan?",
        """SELECT count(*) AS natijalar_soni
FROM laboratory_results
WHERE test_date_time >= CURRENT_DATE AND test_date_time < CURRENT_DATE + 1""",
        ("laboratory_results",),
    ),
    CatalogEntry(
        "Oxirgi 20 ta ko'mir laboratoriya natijasi",
        """SELECT sequence_number AS raqam, test_date_time AS tekshiruv_vaqti,
       moisture_content AS namlik, ash_content AS kullilik, passed_standard AS standartga_mos
FROM laboratory_results
ORDER BY test_date_time DESC NULLS LAST, id DESC LIMIT 20""",
        ("laboratory_results",),
    ),
    CatalogEntry(
        "Uchastkalar bo'yicha ko'mir laboratoriya natijalari soni",
        """SELECT u.name AS uchastka, count(*) AS natijalar_soni
FROM laboratory_results r LEFT JOIN uchastnik u ON u.id = r.uchastka_id
GROUP BY u.id, u.name ORDER BY natijalar_soni DESC, u.name""",
        ("laboratory_results", "uchastnik"),
    ),
    CatalogEntry(
        "Standartga mos kelmagan ko'mir laboratoriya natijalari",
        """SELECT sequence_number AS raqam, test_date_time AS tekshiruv_vaqti,
       moisture_content AS namlik, ash_content AS kullilik, quality_reason AS sabab
FROM laboratory_results WHERE passed_standard IS FALSE
ORDER BY test_date_time DESC NULLS LAST, id DESC""",
        ("laboratory_results",),
    ),
    CatalogEntry(
        "Shu oy vagon hisob dalolatnomalari soni va jami vazni",
        """SELECT count(*) AS dalolatnomalar_soni, sum(total_weight) AS jami_vazn
FROM calculation_acts
WHERE wagon_received_date >= date_trunc('month', CURRENT_DATE)
  AND wagon_received_date < date_trunc('month', CURRENT_DATE) + interval '1 month'""",
        ("calculation_acts",),
    ),
    CatalogEntry(
        "Shu oy avtotransport hisob dalolatnomalari soni va jami vazni",
        """SELECT count(*) AS dalolatnomalar_soni, sum(total_weight) AS jami_vazn
FROM truck_calculation_acts
WHERE truck_received_date >= date_trunc('month', CURRENT_DATE)
  AND truck_received_date < date_trunc('month', CURRENT_DATE) + interval '1 month'
  AND cancelled_at IS NULL""",
        ("truck_calculation_acts",),
    ),
    CatalogEntry(
        "Ko'mir markalari bo'yicha standartlar",
        """SELECT coal_brand AS komir_markasi, "minMoisture" AS minimal_namlik,
       "maxMoisture" AS maksimal_namlik, "minAshContent" AS minimal_kullilik,
       "maxAshContent" AS maksimal_kullilik
FROM coal_standards ORDER BY coal_brand, id""",
        ("coal_standards",),
    ),
    CatalogEntry(
        "Oxirgi 20 ta kunlik radiatsiya o'lchovi",
        """SELECT entry_date AS sana, site_type AS joy_turi,
       radiation_number AS raqam, radiation_level AS radiatsiya_darajasi
FROM daily_radiations ORDER BY entry_date DESC NULLS LAST, id DESC LIMIT 20""",
        ("daily_radiations",),
    ),
    CatalogEntry(
        "TNB partiyalari tahlil holati bo'yicha soni",
        """SELECT "analysisStatus" AS tahlil_holati, count(*) AS partiyalar_soni
FROM tnb_party WHERE archived_at IS NULL
GROUP BY "analysisStatus" ORDER BY partiyalar_soni DESC, "analysisStatus"
""",
        ("tnb_party",),
    ),
]
