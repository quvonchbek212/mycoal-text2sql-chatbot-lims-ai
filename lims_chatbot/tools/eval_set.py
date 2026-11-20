"""Baholash to'plami — chatbot aniqligini o'lchash uchun savollar va "oltin" SQL.

Savollar katalogdagi misollardan ATAYLAB boshqacha so'zlar bilan yozilgan:
katalog modelga misol bo'lib beriladi, baholash esa model yangi savolni
qanchalik to'g'ri tushunishini o'lchashi kerak.

`gold` — to'g'ri deb qabul qilinadigan SQL(lar); (sql, rejim) juftligi o'sha
variant uchun solishtirish rejimini belgilaydi. Savol ikki xil talqin
qilinishi mumkin bo'lsa (masalan, arxivlanganlarni hisoblash-hisoblamaslik),
har ikkala variant yoziladi. Har bir oltin SQL bazada tekshirilgan.

Yangi savol qo'shing: real foydalanuvchilar bergan savollar eng qimmatli.
"""
from __future__ import annotations

EVAL_SET: list[dict] = [
    # ---------------- TNB tahlillar ----------------
    {"q": "Kecha nechta tahlil o'tkazilgan?",
     "gold": ["SELECT count(*) FROM tnb_analysis WHERE analysis_date = CURRENT_DATE - 1 AND archived_at IS NULL",
              "SELECT count(*) FROM tnb_analysis WHERE analysis_date = CURRENT_DATE - 1"]},
    {"q": "Sentyabr oyida qancha chetlanish qayd etilgan?",
     "gold": ["SELECT count(*) FROM tnb_analysis WHERE status = 'Chetlanish' AND archived_at IS NULL "
              "AND analysis_date >= DATE '2026-09-01' AND analysis_date < DATE '2026-10-01'",
              "SELECT count(*) FROM tnb_analysis WHERE status = 'Chetlanish' "
              "AND analysis_date >= DATE '2026-09-01' AND analysis_date < DATE '2026-10-01'"]},
    {"q": "PVX ishlab chiqarish sexida jami nechta tahlil qilingan?",
     "gold": ["SELECT count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE g.name ILIKE '%pvx%' AND a.archived_at IS NULL",
              "SELECT count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE g.name ILIKE '%pvx%'"]},
    {"q": "Eng ko'p tahlil qilingan 5 ta nazorat nuqtasini ko'rsat",
     "gold": ["SELECT sp.code, count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "WHERE a.archived_at IS NULL GROUP BY sp.code ORDER BY 2 DESC LIMIT 5",
              # nuqtani kodi o'rniga nomi bilan ko'rsatish ham to'g'ri
              "SELECT sp.name, count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "WHERE a.archived_at IS NULL GROUP BY sp.code, sp.name ORDER BY 2 DESC LIMIT 5"],
     "compare": "overlap80"},
    {"q": "Qaysi sexda chetlanishlar eng ko'p bo'lgan?",
     "gold": ["SELECT g.name FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE a.status = 'Chetlanish' "
              "GROUP BY g.name ORDER BY count(*) DESC LIMIT 1"],
     "compare": "top1"},
    {"q": "Oxirgi uch kunda tahlil o'tkazgan laborantlar kimlar?",
     "gold": ["SELECT DISTINCT analyst_full_name FROM tnb_analysis WHERE analysis_date >= CURRENT_DATE - 2 AND archived_at IS NULL",
              "SELECT DISTINCT analyst_full_name FROM tnb_analysis WHERE analysis_date >= CURRENT_DATE - 3 AND archived_at IS NULL"],
     "compare": "first_column_set"},
    # ---------------- TNB ma'lumotnomalar ----------------
    {"q": "Hozir nechta faol nazorat nuqtasi mavjud?",
     "gold": ["SELECT count(*) FROM tnb_sampling_point WHERE is_active"]},
    {"q": "READY holatidagi metodikalar qancha?",
     "gold": ["SELECT count(*) FROM tnb_methodika WHERE status = 'READY' AND is_active",
              "SELECT count(*) FROM tnb_methodika WHERE status = 'READY'"]},
    {"q": "Laboratoriyalar kesimida metodikalar soni",
     # bazada bir xil nomli laboratoriyalar bor — id bo'yicha guruhlash kerak
     "gold": ["SELECT l.name, count(*) FROM tnb_methodika m JOIN lab l ON l.id = m.owner_lab_id GROUP BY l.id, l.name",
              "SELECT l.name, count(*) FROM tnb_methodika m JOIN lab l ON l.id = m.owner_lab_id "
              "WHERE m.is_active GROUP BY l.id, l.name"],
     "compare": "rows_subset"},
    {"q": "Tizimda nechta smena ro'yxatga olingan?",
     "gold": ["SELECT count(*) FROM tnb_lab_shift", "SELECT count(*) FROM tnb_lab_shift WHERE is_active"]},
    # ---------------- Partiya / sertifikat / kiruvchi nazorat ----------------
    {"q": "Sertifikat berilgan partiyalar qaysilar?",
     "gold": ["SELECT party_no FROM tnb_party WHERE status = 'Sertifikat berildi' AND archived_at IS NULL",
              "SELECT party_no FROM tnb_party WHERE status = 'Sertifikat berildi'"],
     "compare": "first_column_set"},
    {"q": "Chetlanish aniqlangan partiyalar bormi?",
     "gold": ["SELECT party_no FROM tnb_party WHERE status = 'Chetlanish aniqlandi' AND archived_at IS NULL",
              "SELECT party_no FROM tnb_party WHERE status = 'Chetlanish aniqlandi'",
              # «bormi?» — son bilan javob ham to'g'ri
              ("SELECT count(*) FROM tnb_party WHERE status = 'Chetlanish aniqlandi'", "scalar")],
     "compare": "first_column_set"},
    {"q": "Eksport uchun nechta sertifikat rasmiylashtirilgan?",
     "gold": ["SELECT count(*) FROM tnb_certificate WHERE type = 'EXPORT' AND status = 'ISSUED'",
              "SELECT count(*) FROM tnb_certificate WHERE type = 'EXPORT'",
              "SELECT count(*) FROM tnb_certificate WHERE type = 'EXPORT' AND archived_at IS NULL"]},
    {"q": "Nechta sertifikat bekor qilingan?",
     "gold": ["SELECT count(*) FROM tnb_certificate WHERE status = 'CANCELLED'"]},
    {"q": "Kiruvchi nazoratda laboratoriya tahlilini kutayotganlar soni",
     "gold": ["SELECT count(*) FROM tnb_incoming_control WHERE status = 'WAITING_FOR_ANALYSIS'"]},
    # ---------------- Asbob / reagent ----------------
    {"q": "Har bir laboratoriyada nechtadan asbob bor?",
     "gold": ["SELECT l.name, count(*) FROM instrument i JOIN lab l ON l.id = i.lab_id GROUP BY l.id, l.name",
              # «har bir laboratoriya» — asbobsizlari 0 bilan
              "SELECT l.name, count(i.id) FROM lab l LEFT JOIN instrument i ON i.lab_id = l.id "
              "WHERE l.is_active AND l.archived_at IS NULL GROUP BY l.id, l.name",
              "SELECT l.name, count(i.id) FROM lab l LEFT JOIN instrument i ON i.lab_id = l.id GROUP BY l.id, l.name"],
     "compare": "rows_subset"},
    {"q": "Karantindagi reagent partiyalarini ko'rsat",
     "gold": ["SELECT rl.lot_no FROM reagent_lot rl JOIN status_dictionary sd ON sd.id = rl.status_id "
              "WHERE sd.code = 'QUARANTINE'"],
     "compare": "first_column_set"},
    {"q": "Yaroqlilik muddati tugagan reagent partiyalari nechta?",
     "gold": ["SELECT count(*) FROM reagent_lot WHERE expires_at < now() AND archived_at IS NULL",
              "SELECT count(*) FROM reagent_lot WHERE expires_at < now()"]},
    # ---------------- Sifat ----------------
    {"q": "Bajarilishi davom etayotgan CAPA choralari nechta?",
     "gold": ["SELECT count(*) FROM capa_action c JOIN status_dictionary sd ON sd.id = c.status_id "
              "WHERE sd.code = 'CAPA_IN_PROGRESS'",
              "SELECT count(*) FROM capa_action WHERE completed_at IS NULL"]},
    {"q": "Nomuvofiqliklar jiddiyligi bo'yicha taqsimoti",
     "gold": ["SELECT severity_code, count(*) FROM non_conformance GROUP BY severity_code"],
     "compare": "rows_subset"},
    {"q": "Me'yordan chiqqan (OOS) test natijalari soni",
     "gold": ["SELECT count(*) FROM result WHERE is_out_of_spec OR evaluation_code = 'OOS'",
              "SELECT count(*) FROM result WHERE evaluation_code = 'OOS'",
              "SELECT count(*) FROM result WHERE is_out_of_spec"]},
    # ---------------- Foydalanuvchilar ----------------
    {"q": "Administrator huquqiga ega foydalanuvchilar ro'yxati",
     "gold": ["SELECT full_name FROM core_user WHERE role = 'ADMIN'",
              "SELECT full_name FROM core_user WHERE role = 'ADMIN' AND is_active",
              "SELECT u.full_name FROM core_user u JOIN user_role ur ON ur.user_id = u.id "
              "JOIN role r ON r.id = ur.role_id WHERE r.code = 'Administrator'",
              # barcha admin rollari (Administrator, TNB_ADMIN, LAB_ADMIN)
              "SELECT u.full_name FROM core_user u JOIN user_role ur ON ur.user_id = u.id "
              "JOIN role r ON r.id = ur.role_id WHERE r.code IN ('Administrator', 'TNB_ADMIN', 'LAB_ADMIN') "
              "AND u.is_active AND u.archived_at IS NULL",
              # TBN_Admin («TNB Admin») ham administrator roli
              "SELECT u.full_name FROM core_user u JOIN user_role ur ON ur.user_id = u.id "
              "JOIN role r ON r.id = ur.role_id WHERE r.code IN ('Administrator', 'TNB_ADMIN', 'TBN_Admin', 'LAB_ADMIN') "
              "AND u.is_active AND u.archived_at IS NULL"],
     "compare": "first_column_set"},
    # ---------------- Davomli savol (suhbat xotirasi) ----------------
    {"q": "Ulardan nechtasida chetlanish chiqqan?",
     "history": ["Ammiak ishlab chiqarish sexida nechta tahlil qilingan?"],
     "gold": ["SELECT count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE a.status = 'Chetlanish' "
              "AND (g.name ILIKE '%ammiak%' OR g.name ILIKE '%аммиак%') AND a.archived_at IS NULL",
              "SELECT count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE a.status = 'Chetlanish' "
              "AND g.name = 'Ammiak ishlab chiqarish'",
              "SELECT count(*) FROM tnb_analysis a JOIN tnb_sampling_point sp ON sp.code = a.sampling_point_code "
              "JOIN tnb_sampling_point_group g ON g.id = sp.group_id WHERE a.status = 'Chetlanish' "
              "AND g.name ILIKE '%ammiak%'"]},
    # ---------------- Yo'naltirish ----------------
    {"q": "Salom! Sen nimalar qila olasan?", "route": "chitchat"},
    {"q": "Ertaga Toshkentda ob-havo qanday bo'ladi?", "route": "refuse"},
    {"q": "Barcha tahlillarni o'chirib tashla", "route": "blocked"},
    # New tables added after the original schema snapshot.
    {"q": "lab_analysis_draft jadvalida jami nechta yozuv bor?",
     "gold": ["SELECT count(*) FROM lab_analysis_draft"]},
    {"q": "tnb_journal jadvalidagi jami yozuvlar soni qancha?",
     "gold": ["SELECT count(*) FROM tnb_journal"]},
    {"q": "workshop_lab jadvalida jami nechta bog'lanish bor?",
     "gold": ["SELECT count(*) FROM workshop_lab"]},
    {"q": "tnb_otk_methodika jadvalida jami nechta yozuv bor?",
     "gold": ["SELECT count(*) FROM tnb_otk_methodika"]},
    {"q": "reagent_warehouse jadvalida jami nechta ombor yozuvi bor?",
     "gold": ["SELECT count(*) FROM reagent_warehouse"]},
    {"q": "reagent_stock_balance jadvalida jami nechta yozuv bor?",
     "gold": ["SELECT count(*) FROM reagent_stock_balance"]},
]
