"""Coal LIMS guidance based on PostgreSQL definitions inspected on 2026-11-09.

No row values or inferred foreign keys are assumed here. Status values and
joins must come from the current permission-filtered catalog.
"""

DEFAULT_TABLES = ("laboratory_results", "calculation_acts", "truck_calculation_acts", "coal_standards")

TABLE_NOTES = {
    "laboratory_results": "KO'MIR LABORATORIYA NATIJALARI: namlik moisture_content, kullilik ash_content, standartga moslik passed_standard. Sana test_date_time; uchastka uchastka_id. workflow_type va FK lar natija qaysi dalolatnomaga tegishli ekanini bildiradi.",
    "ash_results": "KULLILIK o'lchovlari: analytical_ash_content, parallel_difference, final_result. laboratory_id orqali laboratoriya natijasiga bog'langan.",
    "lab_result": "QISQA LABORATORIYA NATIJALARI: partiya_raqami, result_date, namlik_wa, kullilik_ad, material_type. O'chirilmagan yozuvlar: deleted IS NOT TRUE.",
    "coal_standards": "KO'MIR STANDARTLARI: coal_brand, namlik va kullilik chegaralari. Katta-kichik harfli ustunlar qo'shtirnoqda yoziladi.",
    "acts": "NAZORAT DALOLATNOMALARI: sequence_number, mining_site, warehouse_name, status.",
    "control_measurement": "NAZORAT O'LCHOVLARI: coalBrand, ashContent, moistureContent, samplingPlace. act_id orqali nazorat dalolatnomasiga bog'langan.",
    "calculation_acts": "VAGON HISOB DALOLATNOMALARI: act_number, coal_brand, party_number, mining_site, total_wagons, total_weight. Sana wagon_received_date.",
    "wagon_info": "DALOLATNOMADAGI VAGONLAR: wagon_number, weight, calculation_act_id. Bekor qilinganlik is_annulled da; bekor qilinmaganlar IS NOT TRUE bilan tanlanadi.",
    "truck_calculation_acts": "AVTOTRANSPORT HISOB DALOLATNOMALARI: act_number, coal_brand, product_type, total_trucks, total_weight. Sana truck_received_date; bekor qilinganlik cancelled_at da.",
    "truck_info": "DALOLATNOMADAGI AVTOTRANSPORT: truck_number, weight, farm_name, truck_calculation_act_id.",
    "gornaya_massa_acts": "TOG' JINSI MASSASI DALOLATNOMALARI: act_number, act_date, coal_brand, mining_site, total_weight, status.",
    "gornaya_massa_wagons": "Tog' jinsi massasi dalolatnomasidagi vagonlar: wagon_number, weight, dispatch_date, gornaya_massa_act_id.",
    "daily_radiations": "KUNLIK RADIATSIYA O'LCHOVLARI: entry_date, site_type, radiation_level, radiation_number.",
    "daily_kaolin_radiations": "KAOLIN RADIATSIYA O'LCHOVLARI: entry_date, kaolin_category, effective_activity_class_1.",
    "calculation_radiation_results": "Hisob dalolatnomasining radiatsiya natijasi: radiation_level, radiation_number.",
    "radiation_spravka": "RADIATSIYA MA'LUMOTNOMALARI: startDate, endDate, branchName, status.",
    "radiation_spravka_items": "Radiatsiya ma'lumotnomasi o'lchovlari: createdAt, radiationLevel, spravka_id.",
    "daily_excavator_work": "EKSKAVATOR ISH JURNALI: work_date, shift, excavator_number, uchastnik_id, status. Bitta ekskavator turli sana/smenalarda takrorlanadi. Jurnaldagi alohida ekskavatorlar soni: COUNT(DISTINCT excavator_number).",
    "excavators": "EKSKAVATORLAR ma'lumotnomasi: name, description. Faqat ma'lumotnomadagi son aniq so'ralganda shu jadval sanaladi. Oddiy jami ekskavatorlar soni daily_excavator_work ish jurnalidagi alohida ekskavatorlarni anglatadi.",
    "uchastnik": "UCHASTKALAR ma'lumotnomasi: name, description.",
    "warehouses": "OMBORLAR ma'lumotnomasi: name.",
    "tnb_analysis": "TNB TAHLILLARI: analysis_date, analyst_full_name, status, party_id, certificate_id. inputs_json va sections_json matn ko'rinishidagi JSON. Natijani nazorat nuqtasiga bog'lash uchun mavjud FK yo'li kerak.",
    "tnb_party": "TNB PARTIYALARI: party_no, product_name, shift_date, status. Tahlil holati katta-kichik harfli analysisStatus ustunida; act_id orqali namuna olish dalolatnomasiga bog'langan.",
    "tnb_act": "TNB NAMUNA OLISH DALOLATNOMALARI: act_no, act_date, party_no, sample_id.",
    "tnb_sample": "TNB NAMUNALARI: serial_no, sampled_date, has_deviation, product_id, sampling_place_id, workshop_id.",
    "tnb_sampling_place": "TNB NAMUNA OLISH JOYLARI: code, name, is_active.",
    "tnb_certificate": "TNB SERTIFIKATLARI: certificate_no, type, issue_date, source_party_id, source_analysis_id. net_weight_tons matn turida.",
    "tnb_defect_slip": "TNB YAROQSIZLIK DALOLATNOMALARI: reason, nonconformity, slipDate, partyNumber, analysis_id.",
    "lab": "LABORATORIYALAR ma'lumotnomasi: code, name, lab_type, is_active.",
    "workshop": "SEXLAR ma'lumotnomasi: code, name, is_active.",
    "status_dictionary": "HOLATLAR LUG'ATI: entity_type, code, label. Status kodini joriy sxemadagi qiymatlar orqali aniqlang.",
    "product_quality_calculation_result": "MAHSULOT SIFAT HISOBLASH NATIJALARI: product_code, source_code, grade, batch_id, sample_id, status; inputs_json va result_json matn ko'rinishidagi JSON.",
}

COLUMN_NOTES = {
    "tnb_party.analysisStatus": "tahlil holati; SQL da katta-kichik harfni saqlab qo'shtirnoqda yozing",
    "laboratory_results.passed_standard": "true = standartga mos; false = mos emas; NULL = baho noma'lum",
    "laboratory_results.test_date_time": "laboratoriya tekshiruvining ish vaqti",
    "coal_standards.maxMoisture": "namlikning yuqori chegarasi",
    "coal_standards.maxAshContent": "kullilikning yuqori chegarasi",
}

SYNONYMS = {
    "tahlil": ("laboratory_results", "tnb_analysis", "result"),
    "analiz": ("laboratory_results", "tnb_analysis"), "анализ": ("laboratory_results", "tnb_analysis"),
    "analysis": ("laboratory_results", "tnb_analysis"),
    "ko'mir": ("laboratory_results", "coal_standards", "calculation_acts"),
    "coal": ("laboratory_results", "coal_standards"), "угол": ("laboratory_results", "coal_standards"),
    "namlik": ("laboratory_results", "lab_result", "coal_standards"),
    "moisture": ("laboratory_results", "coal_standards"), "влажност": ("laboratory_results", "coal_standards"),
    "kullilik": ("ash_results", "laboratory_results", "coal_standards"),
    "kul miqdor": ("ash_results", "laboratory_results"), "ash": ("ash_results", "laboratory_results"),
    "зольност": ("ash_results", "laboratory_results", "coal_standards"),
    "standart": ("coal_standards", "laboratory_results"), "standard": ("coal_standards", "laboratory_results"),
    "chetlanish": ("laboratory_results", "tnb_sample"),
    "vagon": ("wagon_info", "calculation_acts"), "вагон": ("wagon_info", "calculation_acts"),
    "wagon": ("wagon_info", "calculation_acts"),
    "avtotransport": ("truck_calculation_acts", "truck_info"), "truck": ("truck_calculation_acts", "truck_info"),
    "yuk mashina": ("truck_info", "truck_calculation_acts"), "грузов": ("truck_info", "truck_calculation_acts"),
    "radiats": ("daily_radiations", "radiation_spravka", "calculation_radiation_results"),
    "radiation": ("daily_radiations", "radiation_spravka"), "радиац": ("daily_radiations", "radiation_spravka"),
    "kaolin": ("daily_kaolin_radiations", "truck_calculation_acts"),
    "uchastka": ("uchastnik", "laboratory_results", "daily_excavator_work"),
    "ekskavator": ("daily_excavator_work", "excavators"), "excavator": ("daily_excavator_work", "excavators"),
    "ombor": ("warehouses", "acts"), "dalolatnoma": ("acts", "calculation_acts", "truck_calculation_acts"),
    "partiya": ("tnb_party", "batch", "calculation_acts"), "batch": ("batch", "tnb_party"),
    "sertifikat": ("tnb_certificate",), "namuna": ("tnb_sample", "sample"),
    "sex": ("workshop",), "цех": ("workshop",), "laboratoriya": ("lab", "laboratory_results"),
    "asbob": ("instrument",), "kalibrovka": ("instrument_calibration", "instrument"),
    "reagent": ("reagent", "reagent_lot"), "metodika": ("method", "method_version"),
}

ROUTER_RULES = """\
- Ko'mirning namlik/kullilik/sifat natijalari → laboratory_results, ash_results, coal_standards.
- Vagonlar → calculation_acts / wagon_info; avtotransport → truck_calculation_acts / truck_info.
- Radiatsiya → daily_radiations, daily_kaolin_radiations yoki radiation_spravka.
- TNB so'ralsa tnb_*; umumiy LIMS so'ralsa sample, result, test_order, batch.
- Sex → workshop; uchastka → uchastnik; metodika → method / method_version.
- Barcha tanlovlar quyidagi ruxsatli katalog bilan cheklanadi.
"""

DOMAIN_RULES = """\
BAZA HAQIDA:
1. Ko'mir sifat natijalari, TNB tahlillari va umumiy LIMS natijalari alohida modullar.
   Ularni aralashtirma. Qaysi modul nazarda tutilgani aniqlanmasa, qisqa aniqlashtiruvchi savol ber.
2. Ko'mir natijalari laboratory_results da; sana test_date_time. Standartga moslik
   passed_standard: false = mos emas, NULL = noma'lum. quality_status va tolerance_status
   qiymatlarini taxmin qilma. Namlik uchun moisture_content, kullilik uchun ash_content.
3. TNB partiyasining tahlil holati tnb_party."analysisStatus" da. TNB tahlilini
   sex yoki namuna bilan bog'lashda faqat berilgan FK yo'llaridan foydalan.
4. Dalolatnoma vaznini vagon/avtotransport bilan JOIN qilib takroriy yig'ma:
   bir dalolatnomaga bir nechta transport yozuvi tegishli bo'lishi mumkin.
   Vazn birligini sxema yoki savolda ko'rsatilmasa taxmin qilma.
5. archived_at mavjud bo'lsa sanalayotgan obyekt uchun IS NULL; deleted mavjud
   bo'lsa IS NOT TRUE. Guruhlash uchun qo'shilgan ma'lumotnoma jadvallarini filtrlamang.
6. Holat kodlarini faqat CHECK yoki joriy namunalardan ol; noma'lum kodni o'ylab topma.
   status_id uchun sxemadagi FK orqali status_dictionary ga JOIN qil.
7. Sanalar Asia/Tashkent vaqtida. Ish sanasini ishlat; created_at ni faqat
   yozuvning yaratilish vaqti so'ralganda yoki boshqa ish sanasi bo'lmaganda tanla.
8. Nomlar lotin/kirill aralash bo'lishi mumkin. Qidiruvda mos variantlarni qo'sh.
   Obyekt bo'yicha guruhlashda id/kod va nom bo'yicha guruhla.
9. Foydalanuvchi belgilagan hisob: «jami ekskavatorlar nechta», «ekskavatorlar soni»
   va «ish jurnalidagi alohida ekskavatorlar» uchun daily_excavator_work jadvalidagi
   COUNT(DISTINCT excavator_number) ni hisobla. Sana yoki holat faqat savolda so'ralsa
   filtrlanadi. Ishlayotgan ekskavatorlar uchun status = 'WORKING'; bugun so'ralsa
   work_date = CURRENT_DATE. Javobda ish jurnalidagi son ekanini ko'rsat.
   Faqat «ma'lumotnomadagi ekskavatorlar» aniq so'ralsa excavators jadvalini sana.
"""

GLOSSARY = """\
LUG'AT: namlik/moisture/влажность; kullilik/ash/зольность; vagon/wagon/вагон;
avtotransport/truck/грузовик; radiatsiya/radiation/радиация; uchastka/участок;
standartga mos emas → passed_standard IS FALSE (laboratory_results).
"""
