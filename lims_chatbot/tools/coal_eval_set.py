"""Coal acceptance questions, worded differently from prompt examples."""

EVAL_SET = [
    {"q": "Kecha ko'mir bo'yicha qancha laboratoriya natijasi kiritilgan?",
     "gold": ["SELECT count(*) FROM laboratory_results WHERE test_date_time >= CURRENT_DATE - 1 "
              "AND test_date_time < CURRENT_DATE"]},
    {"q": "Ko'mir laboratoriya natijalarining nechtasi standartga mos kelmagan?",
     "gold": ["SELECT count(*) FROM laboratory_results WHERE passed_standard IS FALSE"]},
    {"q": "Ko'mir uchun jami nechta standart yozuvi bor?",
     "gold": ["SELECT count(*) FROM coal_standards"]},
    {"q": "Bugungi radiatsiya o'lchovlari nechta?",
     "gold": ["SELECT count(*) FROM daily_radiations WHERE entry_date = CURRENT_DATE"]},
    {"q": "Ko'mir laboratoriyasida har bir uchastka uchun natijalar nechta?",
     "gold": ["SELECT u.name, count(*) FROM laboratory_results r LEFT JOIN uchastnik u ON u.id=r.uchastka_id "
              "GROUP BY u.id,u.name ORDER BY count(*) DESC,u.name"], "compare": "rows_subset"},
    {"q": "TNB partiyalarini tahlil holatlari bo'yicha sanab ber",
     "gold": ['SELECT "analysisStatus",count(*) FROM tnb_party WHERE archived_at IS NULL '
              'GROUP BY "analysisStatus" ORDER BY count(*) DESC,"analysisStatus"'], "compare": "rows_subset"},
]
