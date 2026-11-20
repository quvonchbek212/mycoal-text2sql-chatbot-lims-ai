"""Domen bilimi — «O'zbek ko'mir LIMS» bazasi haqida qo'lda yozilgan ma'lumot.

Bu fayl modelga baza sxemasida YO'Q narsani aytadi: jadval nima uchun,
qaysi biri asosiy, qaysi ustun qanday ma'noda, qaysi ustunlar FK e'lon
qilinmagan bo'lsa ham amalda bog'langan. Izohlar DDL bloklariga qo'shiladi
(`schema_catalog.render_table`) va jadval tanlashda ishlatiladi.

Hamma ma'lumot bazada tekshirilgan (19.09.2026). QOIDA: izohdagi har bir
jadval/ustun nomi bazada BOR bo'lishi shart — `tests/test_domain.py` buni
`schema/schema.json` bo'yicha tekshiradi.

Izoh o'zgargach ddl.sql ni yangilang (bazasiz):
    python -m lims_chatbot.tools.generate_ddl --render-only
"""
from __future__ import annotations

#: Sxemaga umuman kirmaydigan jadvallar (texnik, foydalanuvchi savoliga aloqasiz).
EXCLUDED_TABLES: set[str] = {"flyway_schema_history"}

# Only these business JSON objects may be decoded by the trusted DB adapter.
# The model cannot call lo_get or supply an arbitrary object identifier.
JSON_LARGE_OBJECT_COLUMNS = {
    ("tnb_analysis", "inputs_json"), ("tnb_analysis", "sections_json"),
    ("tnb_incoming_control", "methodika_ids_json"),
    ("tnb_incoming_control", "methodika_snapshot_json"),
    ("tnb_incoming_control", "indicators_json"),
}

#: FK sifatida e'lon qilinmagan, lekin AMALDA bog'langan ustunlar.
#: Har biri bazada tekshirilgan: to'ldirilgan qiymatlarning (deyarli) hammasi
#: mos keladi. (jadval, ustun, bog'langan_jadval, bog'langan_ustun)
LOGICAL_FKS: list[tuple[str, str, str, str]] = [
    ("tnb_analysis", "sampling_point_code", "tnb_sampling_point", "code"),     # 4426/4426
    ("tnb_analysis", "methodika_id", "tnb_methodika", "id"),                   # 171/171
    ("tnb_analysis", "parameter_id", "tnb_sampling_point_parameter", "id"),    # 158/171
    ("tnb_analysis", "performed_by", "core_user", "id"),
    ("tnb_sampling_point_group", "lab_id", "lab", "id"),
    ("tnb_certificate", "source_party_id", "tnb_party", "id"),
    ("tnb_certificate", "source_analysis_id", "tnb_analysis", "id"),
    ("tnb_incoming_control", "party_id", "tnb_party", "id"),
    ("tnb_journal_entry", "sampling_point_group_id", "tnb_sampling_point_group", "id"),
    ("tnb_lab_shift", "sampling_point_group_id", "tnb_sampling_point_group", "id"),
    ("result", "status_id", "status_dictionary", "id"),
    ("approval_step", "status_id", "status_dictionary", "id"),
    ("approval_workflow", "status_id", "status_dictionary", "id"),
    ("result_measurement", "result_id", "result", "id"),
    ("test_order", "test_definition_id", "test_definition", "id"),
    ("reagent_consumption", "reagent_lot_id", "reagent_lot", "id"),
    ("reagent_consumption", "reagent_id", "reagent", "id"),
    ("instrument_calibration", "instrument_id", "instrument", "id"),
    ("instrument_maintenance", "instrument_id", "instrument", "id"),
    ("instrument_qualification", "instrument_id", "instrument", "id"),
    ("method_version", "method_id", "method", "id"),
    ("non_conformance", "result_id", "result", "id"),
    ("capa_comment", "capa_action_id", "capa_action", "id"),
    ("sampling_task", "sampling_point_id", "sampling_point", "id"),
    ("user_role", "lab_id", "lab", "id"),
]

#: Umumiy modul jadvali → TNB dagi asosiy jadval (ma'lumot shu yerda). Router umumiy modul
#: jadvalini tanlasa (inglizcha «batch» so'zi `batch` nomiga o'xshaydi), asosiysi ham sxemaga qo'shiladi.
MAIN_TABLES: dict[str, str] = {
    "batch": "tnb_party",
    "method": "tnb_methodika",
    "shift": "tnb_lab_shift",
    "workshop": "tnb_sampling_point_group",
}

#: Model SQL yozishdan oldin biladigan umumiy qoidalar (SQL promptiga qo'shiladi).
DOMAIN_RULES = """\
BAZA HAQIDA MUHIM:
1. Bazada ikki quyi tizim bor:
   • TNB (tnb_* jadvallari) — ASOSIY ISH MA'LUMOTLARI: tahlillar (tnb_analysis),
     nazorat nuqtalari (tnb_sampling_point), sexlar (tnb_sampling_point_group),
     metodikalar (tnb_methodika), partiyalar (tnb_party), sertifikatlar
     (tnb_certificate), smenalar (tnb_lab_shift).
   • Umumiy LIMS moduli: sample, test_order, result, instrument, reagent_lot,
     non_conformance, capa_action va h.k. — bularda ma'lumot kam.
   «Tahlil», «analiz», «me'yor/norma», «chetlanish», «nazorat nuqtasi», «sex»,
   «metodika» haqidagi savollar odatda TNB jadvallariga tegishli.
2. Tahlil natijasi tnb_analysis.status da: 'Norma' — me'yorda, 'Chetlanish' —
   me'yordan chetga chiqqan. Tahlilning sexi: tnb_analysis.sampling_point_code =
   tnb_sampling_point.code → tnb_sampling_point.group_id = tnb_sampling_point_group.id.
3. `status_id` ustunlari status_dictionary.id ga bog'langan: holatni
   JOIN status_dictionary sd ON sd.id = <jadval>.status_id qilib sd.code bo'yicha
   filtrlang (sd.label — o'zbekcha nomi). status_id ni matn bilan solishtirmang.
4. Nomlar o'zbekcha (lotin) VA ruscha (kirill) aralash yozilgan. Nom bo'yicha
   qidirganda ikkala variantni ham qo'shing:
   (name ILIKE '%ammiak%' OR name ILIKE '%аммиак%').
5. archived_at IS NOT NULL — arxivlangan (o'chirilgan) yozuv. Foydalanuvchi
   alohida so'ramasa, SANALAYOTGAN jadvalda (savolda soni yoki ro'yxati so'ralgan
   narsa: «metodikalar soni» → tnb_methodika) faqat archived_at IS NULL
   yozuvlarni hisoblang. Guruhlash/nom uchun qo'shilgan ma'lumotnoma jadvallariga
   (lab, workshop, tnb_sampling_point_group ...) is_active/archived_at filtrini
   QO'YMANG, hatto ular FROM da birinchi tursa ham — aks holda ularga bog'langan
   yozuvlar hisobdan tushib qoladi.
   «Faol» so'ralsa — is_active ni sanalayotgan jadvalning o'ziga qo'ying.
6. «[har doim NULL]» — eski snapshot kuzatuvi, yangi qiymatlar bo'lishi mumkin.
   oid ustunlardan faqat [xavfsiz JSON o'qish] belgilanganini alohida ustun sifatida
   SELECT qilish mumkin: adapter mazmunni chegaralab, maxfiy kalitlarni niqoblaydi.
   Bu ustunlarga CAST/funksiya/operator qo'llamang. Boshqa oid ustunlarni SELECT qilmang.
   Ro'yxatda id ustunlari o'rniga nom/raqam ko'rsating.
7. Sanalar Asia/Tashkent vaqtida. «Bugun» = CURRENT_DATE.
8. Obyekt bo'yicha guruhlaganda uning KODI bo'yicha guruhlang (nom takrorlanishi
   mumkin): GROUP BY sp.code, sp.name — nazorat nuqtalari nomlari takrorlanadi.
9. «Bormi?» savoliga ro'yxat qaytaring (bo'sh bo'lsa — yo'q degani).
"""

#: Foydalanuvchi atamasi → bazadagi jadval (SQL promptidagi lug'at).
GLOSSARY = """\
LUG'AT (foydalanuvchi atamasi → jadval). Savol rus yoki ingliz tilida bo'lsa — ma'nosi bo'yicha
shu lug'atga keltiring: анализ/analysis → tahlil, отклонение/deviation → chetlanish,
точка контроля/control point → nazorat nuqtasi, цех/workshop → sex, партия/batch → partiya (tnb_party),
прибор/instrument → asbob. Sana bo'yicha filtr — jadvalning ish sanasi (tnb_analysis.analysis_date), created_at emas.
  tahlil/analiz/natija (TNB) → tnb_analysis · chetlanish → tnb_analysis.status = 'Chetlanish'
  nazorat nuqtasi / namuna olish nuqtasi → tnb_sampling_point · sex/bo'lim → tnb_sampling_point_group
  metodika/МВИ/ГОСТ usuli → tnb_methodika · ko'rsatkich/parametr → tnb_sampling_point_parameter
  partiya → tnb_party · sertifikat → tnb_certificate · akt (namuna olish dalolatnomasi) → tnb_act
  brak/yaroqsizlik dalolatnomasi → tnb_defect_slip · kiruvchi nazorat → tnb_incoming_control
  smena → tnb_lab_shift · jurnal → tnb_journal_entry / tnb_journal_template
  laboratoriya → lab · asbob/uskuna → instrument · kalibrovka → instrument_calibration
  reagent → reagent, reagent_lot (partiyalari), reagent_consumption (sarfi)
  nomuvofiqlik/NC → non_conformance · tuzatuvchi chora/CAPA → capa_action
  LIMS namunasi → sample · test buyurtmasi → test_order · test natijasi → result
  reglament → regulation · normativ hujjat → normative_document · mahsulot → product
  foydalanuvchi/xodim → core_user · umumiy rol → core_user.role (ADMIN, USER ...)
  batafsil rollar (laborant, TNB admin, sex boshlig'i ...) → user_role → role (role.code)
  holatlar lug'ati → status_dictionary
"""

#: Leksik zaxira tanlash uchun: savoldagi so'z (bo'lagi) → jadvallar.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "tahlil": ("tnb_analysis",), "analiz": ("tnb_analysis",), "анализ": ("tnb_analysis",),
    "chetlanish": ("tnb_analysis",), "norma": ("tnb_analysis", "tnb_sampling_point_parameter"),
    "me'yor": ("tnb_sampling_point_parameter", "tnb_analysis"),
    "nazorat nuqta": ("tnb_sampling_point",), "nuqta": ("tnb_sampling_point",), "точк": ("tnb_sampling_point",),
    "sex": ("tnb_sampling_point_group", "workshop"), "цех": ("tnb_sampling_point_group", "workshop"),
    "bo'lim": ("tnb_sampling_point_group",),
    "metodika": ("tnb_methodika",), "методик": ("tnb_methodika",), "мви": ("tnb_methodika",),
    "parametr": ("tnb_sampling_point_parameter",), "ko'rsatkich": ("tnb_sampling_point_parameter",),
    "partiya": ("tnb_party",), "партия": ("tnb_party",),
    "sertifikat": ("tnb_certificate",), "сертификат": ("tnb_certificate",),
    "akt": ("tnb_act",), "dalolatnoma": ("tnb_act", "tnb_defect_slip"), "brak": ("tnb_defect_slip",),
    "kiruvchi": ("tnb_incoming_control",), "xomashyo": ("tnb_incoming_control",),
    "smena": ("tnb_lab_shift",), "смена": ("tnb_lab_shift",),
    "jurnal": ("tnb_journal_entry", "tnb_journal_template"), "журнал": ("tnb_journal_entry",),
    "laboratoriya": ("lab",), "лаборатор": ("lab",),
    "asbob": ("instrument",), "uskuna": ("instrument",), "прибор": ("instrument",),
    "kalibrovka": ("instrument_calibration", "instrument"), "калибров": ("instrument_calibration",),
    "reagent": ("reagent", "reagent_lot"), "реактив": ("reagent", "reagent_lot"),
    "nomuvofiqlik": ("non_conformance",), "capa": ("capa_action",),
    "namuna": ("sample", "tnb_sample"), "проба": ("sample", "tnb_sample"),
    "reglament": ("regulation",), "normativ": ("normative_document",),
    "mahsulot": ("product",), "foydalanuvchi": ("core_user",), "xodim": ("core_user",),
    "rol": ("role", "user_role"),
}

#: Jadval izohlari. BIRINCHI QATOR — jadval tanlashdagi qisqa ta'rif.
TABLE_NOTES: dict[str, str] = {
    # ------------------------------ TNB ------------------------------
    "tnb_analysis": (
        "TNB laboratoriya TAHLILLARI — asosiy ish jurnali: har yozuv bitta nazorat nuqtasi bo'yicha bitta tahlil.\n"
        "status: 'Norma' (me'yorda) yoki 'Chetlanish' (me'yordan chetga chiqqan). Sana: analysis_date.\n"
        "Nazorat nuqtasi: sampling_point_code = tnb_sampling_point.code; sexi: tnb_sampling_point.group_id →\n"
        "tnb_sampling_point_group.name. Partiya: party_id → tnb_party. Tahlilchi: analyst_full_name.\n"
        "O'lchangan qiymatlar inputs_json/sections_json da: ularni alohida ustun sifatida tanlasa, xavfsiz adapter JSON mazmunini qaytaradi."
    ),
    "tnb_sampling_point": (
        "TNB NAZORAT NUQTALARI (namuna olinadigan joylar): code, name (ko'pincha ruscha), sexi group_id.\n"
        "tnb_analysis.sampling_point_code shu jadvalning code ustuniga teng. code noyob, name TAKRORLANADI —\n"
        "nuqta bo'yicha guruhlashda GROUP BY sp.code, sp.name."
    ),
    "tnb_sampling_point_group": (
        "SEXLAR / BO'LIMLAR — TNB nazorat nuqtalari guruhi (masalan 'Ammiak ishlab chiqarish', 'Цех №56').\n"
        "Laboratoriyasi: lab_id → lab."
    ),
    "tnb_sampling_point_parameter": (
        "Nazorat nuqtasida o'lchanadigan KO'RSATKICHLAR (parametrlar): description — nomi, norm — me'yor (matn),\n"
        "periodicity — davriyligi (matn, masalan 'Smenada 2 marta')."
    ),
    "tnb_sampling_point_methodika": "Nazorat nuqtasi ↔ metodika bog'lanishi va tahlil chastotasi (frequency_*).",
    "tnb_sampling_point_parameter_methodika": "Ko'rsatkich (parametr) ↔ metodika bog'lanishi.",
    "tnb_sampling_point_laboratory": "Nazorat nuqtasi ↔ sex/laboratoriya guruhi bog'lanishi (group_id → tnb_sampling_point_group).",
    "tnb_sampling_point_location": "Nazorat nuqtasining joylashuvi (matn).",
    "tnb_sampling_point_norm": "Nazorat nuqtasi me'yorlari (matn).",
    "tnb_methodika": (
        "TAHLIL METODIKALARI (МВИ, ГОСТ, O'z DSt): code, name (ko'pincha ruscha), status 'DRAFT'/'READY',\n"
        "egasi owner_lab_id → lab, owner_group_id → tnb_sampling_point_group."
    ),
    "tnb_user_methodika": "Foydalanuvchining shaxsiy metodika nusxalari (tnb_methodika dan olingan).",
    "tnb_methodika_submission": "Metodika qo'shish arizalari (ko'rib chiqish holati bilan).",
    "tnb_party": (
        "TAYYOR MAHSULOT PARTIYALARI (smena bo'yicha): party_no, product_name, shift_date, shift_type.\n"
        "status (o'zbekcha): 'Tahlil kutilmoqda', 'Tahlil yakunlandi', 'Sertifikat berildi', 'Chetlanish aniqlandi'.\n"
        "Tahlil holati uchun analysis_status ustunidan foydalaning (\"analysisStatus\" — uning eski nusxasi)."
    ),
    "tnb_certificate": (
        "SIFAT SERTIFIKATLARI: certificate_no, type 'LOCAL'/'EXPORT', status 'ISSUED'/'CANCELLED', issue_date.\n"
        "net_weight_tons — MATN turida (hisoblash uchun ::numeric kerak). Partiyasi: source_party_id → tnb_party."
    ),
    "tnb_act": "NAMUNA OLISH DALOLATNOMALARI (akt): act_no, act_date, party_no, sample_id → tnb_sample.",
    "tnb_sample": "TNB NAMUNALARI (tayyor mahsulotdan): sampled_date, product_id → product, has_deviation (chetlanish bormi).",
    "tnb_defect_slip": "YAROQSIZLIK (BRAK) DALOLATNOMALARI: reason, party_id → tnb_party, analysis_id → tnb_analysis.",
    "tnb_incoming_control": "KIRUVCHI XOMASHYO NAZORATI: status, supplier (yetkazib beruvchi matni), quantity_tons, arrived_at.",
    "tnb_product_output": "Tayyor mahsulot chiqarish (jo'natish) yozuvlari: output_date, total_quantity_tons.",
    "tnb_product_output_vehicle": "Mahsulot chiqarishdagi transport vositalari (vagon/yuk mashinasi).",
    "tnb_product": "TNB mahsulotlari qisqa ro'yxati (asosiy mahsulotlar ro'yxati — product jadvalida).",
    "tnb_journal_template": "LABORATORIYA JURNALLARI shablonlari (qaysi jurnal, qaysi nuqta uchun).",
    "tnb_journal_template_version": "Jurnal shablonlarining versiyalari.",
    "tnb_journal_entry": "Laboratoriya jurnaliga kiritilgan yozuvlar: entry_date, status 'DRAFT'/'SIGNED'.",
    "tnb_lab_shift": "SMENALAR ro'yxati va vaqtlari (start_time, end_time).",
    "tnb_shift_handover": "Smena topshirish-qabul qilish yozuvlari.",
    "tnb_analysis_request": "TNB TAHLIL SO'ROVLARI: status 'REQUESTED'/'DONE', urgency, requested_at.",
    "tnb_user_scope": "Foydalanuvchiga biriktirilgan nuqta/metodika/guruhlar (ruxsat doirasi).",
    "tnb_user_page_access": "Foydalanuvchi sahifa ruxsatlari (texnik).",
    "tnb_product_settings": "Mahsulot sozlamalari (texnik JSON).",
    # ------------------------------ umumiy LIMS ------------------------------
    "sample": (
        "LIMS NAMUNALARI (umumiy modul): sample_no, lab_id → lab, taken_at, received_at.\n"
        "Holati: status_id → status_dictionary (entity_type 'SAMPLE')."
    ),
    "test_order": "Namuna bo'yicha TEST BUYURTMALARI: sample_id → sample, test_definition_id, status_id → status_dictionary.",
    "result": (
        "TEST NATIJALARI (umumiy modul): numeric_value, is_out_of_spec (me'yordan tashqari),\n"
        "evaluation_code 'PASS'/'OOS', test_order_id → test_order, status_id → status_dictionary."
    ),
    "result_measurement": "Natijaning alohida o'lchovlari (result_id → result).",
    "result_revision": "Natija o'zgarishlari tarixi.",
    "test_definition": "TEST (ko'rsatkich) TA'RIFLARI: code, name, o'lchov birligi.",
    "specification": "SPETSIFIKATSIYALAR (mahsulot sifat talablari to'plami).",
    "specification_item": "Spetsifikatsiya bandlari: min_value, max_value, target_value (me'yorlar).",
    "batch": (
        "PARTIYALAR (umumiy modul; asosiy partiyalar — tnb_party): batch_no, status_id → status_dictionary.\n"
        "«Partiya/партия/batch» so'ralsa odatda tnb_party kerak; bu jadval — faqat umumiy modul so'ralsa."
    ),
    "production_batch": "ISHLAB CHIQARISH PARTIYALARI: batch_number, status, product_id → product.",
    "instrument": (
        "ASBOB-USKUNALAR: code, name, lab_id → lab, calibration_due_at (keyingi kalibrovka muddati),\n"
        "maintenance_due_at, metrology_state, holati status_id → status_dictionary (entity_type 'INSTRUMENT')."
    ),
    "instrument_calibration": "ASBOBLAR KALIBROVKASI: calibration_date, due_at, outcome_code, certificate_no, instrument_id → instrument.",
    "instrument_maintenance": "Asboblarga texnik xizmat ko'rsatish: maintenance_type, scheduled_at, completed_at.",
    "instrument_qualification": "Asboblar kvalifikatsiyasi (IQ/OQ): qualification_type, qualified_at, due_at.",
    "instrument_metrology_schedule": "Asboblar metrologik tekshiruv REJASI: schedule_year, planned_month.",
    "reagent": "REAGENTLAR (kimyoviy moddalar) ro'yxati: code, name, min_stock_level.",
    "reagent_lot": (
        "REAGENT PARTIYALARI (zaxira): lot_no, expires_at (yaroqlilik muddati), available_quantity,\n"
        "reagent_id → reagent, holati status_id → status_dictionary (entity_type 'REAGENT_LOT')."
    ),
    "reagent_consumption": "REAGENT SARFI: quantity, consumed_at, reagent_lot_id → reagent_lot.",
    "non_conformance": (
        "NOMUVOFIQLIKLAR (NC): nc_no, title, severity_code, identified_at, due_at,\n"
        "holati status_id → status_dictionary (entity_type 'NON_CONFORMANCE')."
    ),
    "capa_action": (
        "TUZATUVCHI/OLDINI OLUVCHI CHORALAR (CAPA): title, due_at, completed_at, non_conformance_id,\n"
        "holati status_id → status_dictionary (entity_type 'CAPA_ACTION')."
    ),
    "capa_comment": "CAPA bo'yicha izohlar.",
    "quality_decision": "SIFAT QARORLARI (partiya/namuna bo'yicha): decision_no, decided_at, status_id.",
    "quality_document": "SIFAT HUJJATLARI (pasport, protokol): document_no, document_type, lifecycle_status.",
    "method": "LIMS METODLARI (umumiy modul): code, name, lab_id. TNB metodikalari esa tnb_methodika da.",
    "method_version": "Metod versiyalari: version_no, lifecycle_status, is_current.",
    "lab": "LABORATORIYALAR: name, is_active, is_reagent_producer. Lab turi alohida ustun sifatida mavjud emas.",
    "workshop": "SEXLAR (umumiy modul ro'yxati): code, name. TNB tahlillaridagi sex — tnb_sampling_point_group.",
    "section": "Sex uchastkalari (workshop_id → workshop).",
    "sampling_point": "Umumiy moduldagi namuna olish nuqtalari (TNB nuqtalari esa tnb_sampling_point da).",
    "plant": "Korxonalar ma'lumotnomasi (code, name).",
    "product": "MAHSULOTLAR ro'yxati: code, name (karbamid, ammiakli selitra va h.k.).",
    "core_user": (
        "FOYDALANUVCHILAR (xodimlar): full_name, username, is_active, last_login_at.\n"
        "role — umumiy tizim roli (ADMIN/MANAGER/ANALYST/REVIEWER/USER). Batafsil rollar — user_role → role."
    ),
    "role": (
        "ROLLAR ro'yxati: code (LAB_ANALYST, TNB_ADMIN, LAB_GROUP_ADMIN, Administrator ...), name (o'zbekcha).\n"
        "Administrator rollari: code IN ('Administrator', 'TNB_ADMIN', 'TBN_Admin', 'LAB_ADMIN').\n"
        "LAB_GROUP_ADMIN — laboratoriya boshlig'i (administrator emas). Rolni code bo'yicha aniq filtrlang, ILIKE emas."
    ),
    "user_role": "Foydalanuvchi ↔ batafsil rol biriktiruvi: user_id → core_user, role_id → role.",
    "permission": "Ruxsatlar ro'yxati (texnik).",
    "role_permission": "Rol ↔ ruxsat bog'lanishi (texnik).",
    "status_dictionary": (
        "HOLATLAR LUG'ATI: entity_type (qaysi jadval uchun), code, label (o'zbekcha nomi).\n"
        "Boshqa jadvallardagi status_id shu jadvalning id siga teng."
    ),
    "audit_log": "O'ZGARISHLAR JURNALI (audit): kim (actor_name_cache), qachon (occurred_at), qaysi obyektda nima qildi.",
    "sampling_task": "NAMUNA OLISH TOPSHIRIQLARI: task_no, status, planned_at, due_at, is_overdue.",
    "sampling_task_event": "Namuna olish topshiriqlari hodisalari tarixi.",
    "sampling_plan": "Namuna olish rejalari.",
    "lab_analysis_request": "LABORATORIYA TAHLIL SO'ROVLARI (umumiy modul): request_no, status, priority, requested_at, is_overdue.",
    "regulation": "TEXNOLOGIK REGLAMENTLAR: code, title, status, effective_date, valid_until.",
    "normative_document": "NORMATIV HUJJATLAR (GOST, O'z DSt, TU): code, name, document_family, valid_until.",
    "stability_study": "Barqarorlik tadqiqotlari.",
    "shipment": "JO'NATMALAR (ERP dan): shipment_no, customer_name, product_name, quantity, shipped_at.",
    "supplier": "YETKAZIB BERUVCHILAR ro'yxati.",
    "unit_of_measure": "O'lchov birliklari.",
    "elements": "Kimyoviy elementlar ma'lumotnomasi (Mendeleyev jadvali).",
    "environmental_control_analysis": "EKOLOGIK NAZORAT tahlillari (oqova suv, chiqindi gazlar).",
    "lab_analytical_control_journal_entry": "Analitik nazorat jurnali yozuvlari: analysis_date, shift_name.",
    "shift": "Smenalar (umumiy modul). TNB smenalari — tnb_lab_shift.",
    "sample_type": "Namuna turlari ma'lumotnomasi.",
    "priority": "Ustuvorlik darajalari ma'lumotnomasi.",
    "reject_reason": "Rad etish sabablari ma'lumotnomasi.",
}

#: Ustun izohlari: "jadval.ustun" → izoh.
COLUMN_NOTES: dict[str, str] = {
    "tnb_analysis.status": "'Norma' = me'yorda, 'Chetlanish' = me'yordan chetga chiqqan",
    "tnb_analysis.sampling_point_code": "= tnb_sampling_point.code",
    "tnb_party.analysis_status": "tahlil holati (shu ustunni ishlating)",
    "tnb_certificate.net_weight_tons": "matn! yig'ish uchun net_weight_tons::numeric",
    "instrument.calibration_due_at": "keyingi kalibrovka muddati (< now() → muddati o'tgan)",
    "reagent_lot.expires_at": "yaroqlilik muddati (< now() → muddati o'tgan)",
    "result.is_out_of_spec": "true → me'yordan tashqari (OOS)",
}
