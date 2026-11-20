-- =====================================================================
--  «O'zbek ko'mir LIMS» — baza sxemasi (DDL)
--  AVTOMATIK YARATILGAN: 2026-11-09T11:29:51+00:00   |   Manba: 192.168.1.27:5432/mycoallimsdb   |   Jadvallar: 137
--
--  Chatbot bazani AYNAN shu ma'lumot orqali "ko'radi": model shundan SQL
--  yozadi, SQL tekshiruvchisi ham jadval/ustun/qiymatlarni shunga qarab
--  tekshiradi. QO'LDA TAHRIRLAMANG — baza o'zgarganda qayta yarating:
--      python -m lims_chatbot.tools.generate_ddl
--  Domen izohlari (`-- ` qatorlari jadval ustida) lims_chatbot/app/domain.py
--  da yoziladi; ularni o'zgartirgach:  ... generate_ddl --render-only
--
--  Belgilar:
--    RUXSAT: …        — CHECK bo'yicha ruxsat etilgan qiymatlar
--    BAZADA: 'X' N    — bazada haqiqatda uchraydigan qiymat va soni
--    ISHLATILMAGAN: … — ruxsat etilgan, lekin bazada YO'Q (filtr doim 0 beradi)
--    [har doim NULL]  — ustun bo'sh, ishlatmang
--    oraliq: A … B    — sana ustunidagi eng kichik va eng katta qiymat
-- =====================================================================

-- TABLE: act_spravkas  (satrlar: 3)
CREATE TABLE act_spravkas (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-09-19
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-09-25
    created_by varchar,
    spravka_date date NOT NULL,  -- oraliq: 2026-08-27 … 2026-09-19
    spravka_number varchar,
    status varchar,  -- BAZADA: 'CLOSED' 3
    PRIMARY KEY (id)
);

-- TABLE: acts  (satrlar: 1379)
-- NAZORAT DALOLATNOMALARI: sequence_number, mining_site, warehouse_name, status.
CREATE TABLE acts (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    enterprise_rep varchar NOT NULL,
    lab_delivery_time varchar,
    master_otk_name varchar NOT NULL,
    mining_site varchar NOT NULL,
    sampling_time varchar NOT NULL,
    sequence_number bigint,
    status varchar,  -- RUXSAT: 'CREATED', 'SENT_TO_CRUSHER', 'SENT_TO_LAB', 'SENT_TO_SECTION_MASTER', 'LAB_ACCEPTED', 'SECTION_MASTER_ACCEPTED', 'SENT_TO_ACT', 'ACT_ACCEPTED', 'ACT_COMPLETED'; BAZADA: 'ACT_COMPLETED' 781, 'SENT_TO_ACT' 570, 'SECTION_MASTER_ACCEPTED' 12, 'LAB_ACCEPTED' 11, 'SENT_TO_LAB' 4, 'ACT_ACCEPTED' 1; ISHLATILMAGAN: CREATED, SENT_TO_CRUSHER, SENT_TO_SECTION_MASTER
    warehouse_name varchar,  -- [har doim NULL — ishlatmang]
    section_master_approved boolean,
    PRIMARY KEY (id)
);

-- TABLE: analysis_resource_requirement  (satrlar: 0 — BO`SH)
CREATE TABLE analysis_resource_requirement (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    analysis_code varchar NOT NULL,
    analysis_name varchar NOT NULL,
    gas_id varchar,
    instrument_id varchar,
    reagent_id varchar,
    is_required boolean NOT NULL,
    resource_code varchar NOT NULL,
    resource_name varchar NOT NULL,
    resource_type varchar NOT NULL,  -- RUXSAT: 'EQUIPMENT', 'AUXILIARY_EQUIPMENT', 'REACTIVE_GAS', 'REAGENT'
    sort_order integer NOT NULL,
    source_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(id),
    FOREIGN KEY (source_id) REFERENCES product_quality_source(id),
    FOREIGN KEY (gas_id) REFERENCES gas(id),
    FOREIGN KEY (reagent_id) REFERENCES reagent(id)
);

-- TABLE: approval_step  (satrlar: 0 — BO`SH)
CREATE TABLE approval_step (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    acted_at timestamptz,
    acted_by_user_id varchar,
    approver_user_id varchar,
    comment varchar,
    is_current boolean,
    role_code varchar,
    status_id varchar,
    step_name varchar,
    step_no integer,
    template_step_id varchar,
    workflow_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: approval_workflow  (satrlar: 0 — BO`SH)
CREATE TABLE approval_workflow (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    comment varchar,
    completed_at timestamptz,
    current_step_no integer,
    entity_id varchar,
    entity_type varchar,
    plant_id varchar,
    result_id varchar,
    started_at timestamptz,
    started_by_user_id varchar,
    status_id varchar,
    template_id varchar,
    workflow_no integer,
    PRIMARY KEY (id)
);

-- TABLE: approval_workflow_template  (satrlar: 0 — BO`SH)
CREATE TABLE approval_workflow_template (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar,
    entity_type varchar,
    is_active boolean,
    is_default boolean,
    lab_id varchar,
    name varchar,
    plant_id varchar,
    separation_of_duty boolean,
    PRIMARY KEY (id)
);

-- TABLE: approval_workflow_template_step  (satrlar: 0 — BO`SH)
CREATE TABLE approval_workflow_template_step (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    approver_user_id varchar,
    role_code varchar,
    step_name varchar,
    step_no integer,
    template_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: ash_results  (satrlar: 0 — BO`SH)
-- KULLILIK o'lchovlari: analytical_ash_content, parallel_difference, final_result. laboratory_id orqali laboratoriya natijasiga bog'langan.
CREATE TABLE ash_results (
    id bigint NOT NULL,
    analytical_ash_content numeric(10,2),
    created_at timestamptz NOT NULL,
    final_result numeric(10,2),
    first_aa numeric(10,2),
    first_final_mass numeric(19,2),
    first_sample_mass numeric(19,6),
    first_m1 numeric(19,6),
    first_m2 numeric(19,6),
    first_m3 numeric(19,6),
    first_m4 numeric(19,6),
    first_m5 numeric(19,6),
    parallel_difference numeric(10,2),
    second_aa numeric(10,2),
    second_final_mass numeric(19,2),
    second_sample_mass numeric(19,6),
    second_m1 numeric(19,6),
    second_m2 numeric(19,6),
    second_m3 numeric(19,6),
    second_m4 numeric(19,6),
    second_m5 numeric(19,6),
    selected_pair varchar,  -- RUXSAT: 'FIRST_SECOND', 'FIRST_THIRD', 'SECOND_THIRD'
    third_aa numeric(10,2),
    third_final_mass numeric(19,2),
    third_sample_mass numeric(19,6),
    third_m1 numeric(19,6),
    third_m2 numeric(19,6),
    third_m3 numeric(19,6),
    third_m4 numeric(19,6),
    third_m5 numeric(19,6),
    tolerance numeric(10,2),
    updated_at timestamptz NOT NULL,
    laboratory_id bigint NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (laboratory_id) REFERENCES laboratory_results(id)
);

-- TABLE: audit_log  (satrlar: 6406)
CREATE TABLE audit_log (
    id varchar NOT NULL,
    action_code varchar NOT NULL,  -- BAZADA: 'laboratory.result.create' 2941, 'users.list.read' 966, 'org.labs.read' 301, 'org.workshops.read' 291, 'org.plants.read' 282, 'access-control.roles.read' 272, 'approvals.templates.list.read' 254, 'documents.templates.list.read' 254, 'act.measurement.edit' 179, 'act.measurement.update' 179, 'users.create' 119, 'act.measurement.remove' 113, 'dictionaries.statuses.read' 63, 'batches.list.read' 46, 'dictionaries.sample-types.read' 39, 'dictionaries.priorities.read' 17, 'dictionaries.sample-sources.read' 17, 'dictionaries.sample-storage-locations.read' 17, 'org.shifts.read' 17, 'samples.list.read' 13, 'act.measurement.remove_skipped' 11, 'integrations.shipments.read' 7, 'non-conformances.list.read' 2, 'quality-decisions.list.read' 2, 'users.update' 2, … yana 2 ta
    actor_name_cache varchar,
    actor_user_id varchar,
    comment varchar,
    diff_json jsonb,  -- [JSON matn]
    entity_id varchar NOT NULL,
    entity_type varchar NOT NULL,  -- BAZADA: 'LaboratoryResult' 2941, 'User' 1089, 'Measurement' 303, 'Lab' 301, 'Workshop' 291, 'Plant' 282, 'Role' 272, 'ApprovalWorkflowTemplate' 254, 'DocumentTemplate' 254, 'MeasurementEntity' 179, 'StatusDictionary' 63, 'Batch' 46, 'SampleTypeDictionary' 39, 'PriorityDictionary' 17, 'SampleSourceDictionary' 17, 'SampleStorageLocationDictionary' 17, 'Shift' 17, 'Sample' 13, 'Shipment' 7, 'NonConformance' 2, 'QualityDecision' 2
    ip_address varchar,
    new_value_json jsonb,  -- [JSON matn]
    occurred_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    old_value_json jsonb,  -- [JSON matn]
    plant_id varchar,
    request_id varchar,
    source_system varchar,  -- BAZADA: 'lims-web' 6406
    PRIMARY KEY (id),
    FOREIGN KEY (actor_user_id) REFERENCES core_user(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: batch  (satrlar: 0 — BO`SH)
CREATE TABLE batch (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    batch_no varchar NOT NULL,
    control_note varchar,
    hold_until timestamptz,
    is_active boolean NOT NULL,
    plant_id varchar NOT NULL,
    reject_comment varchar,
    reject_reason_id varchar,
    rejected_at timestamptz,
    rejected_by_user_id varchar,
    source_document_no varchar,
    status_changed_at timestamptz,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    supplier_id varchar,
    workshop_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id)
);

-- TABLE: calculation_acts  (satrlar: 872)
-- VAGON HISOB DALOLATNOMALARI: act_number, coal_brand, party_number, mining_site, total_wagons, total_weight. Sana wagon_received_date.
CREATE TABLE calculation_acts (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    act_number varchar,
    arbitration_sample_weight float8,
    chunk_size_actual varchar,
    chunk_size_norm varchar,
    coal_brand varchar,
    coal_brand_seq bigint,
    destination text,
    fine_fraction_actual float8,
    fine_fraction_norm float8,  -- [har doim NULL — ishlatmang]
    lab_sample_weight float8,
    master_otk_checked_by varchar,
    master_otk_name varchar,
    master_section_name varchar,
    mineral_impurities_actual float8,
    mineral_impurities_norm float8,
    mining_site varchar,
    party_number varchar,
    party_volume float8,
    radiation_checked_by varchar,
    standard_name varchar,
    status varchar,  -- BAZADA: 'YAKUNLANDI' 705, 'YUBORILDI' 80, 'OTK_GA_YUBORILDI' 34, 'DROBILKADAN_OLINDI' 20, 'TAYYOR' 20, 'DROBILKADA' 8, 'QISMAN_YAKUNLANDI' 3, 'KUTILMOQDA' 2
    total_wagons integer,
    total_weight float8,
    uchastka_checked_by varchar,
    wagon_received_date timestamp,  -- oraliq: 2026-09-05 … 2026-11-09
    zbit_checked_by varchar,
    radiation_result_id varchar,
    departure_track varchar,
    departure_branch varchar,
    departure_station varchar,
    zbit_received_at timestamptz,  -- oraliq: 2026-10-06 … 2026-11-09
    closed_at timestamptz,  -- oraliq: 2026-10-27 … 2026-11-09
    closed_by varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (radiation_result_id) REFERENCES calculation_radiation_results(id)
);

-- TABLE: calculation_monthly_spravka_items  (satrlar: 1)
CREATE TABLE calculation_monthly_spravka_items (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-08-27
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-08-27
    act_count integer,
    average_ash float8,
    average_moisture float8,
    coal_brand varchar NOT NULL,
    total_weight float8,
    spravka_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (spravka_id) REFERENCES calculation_monthly_spravkas(id)
);

-- TABLE: calculation_monthly_spravkas  (satrlar: 1)
CREATE TABLE calculation_monthly_spravkas (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-08-27
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-27 … 2026-08-27
    created_by varchar,
    grand_total float8,
    month integer NOT NULL,
    spravka_number varchar,
    year integer NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: calculation_radiation_results  (satrlar: 1313)
-- Hisob dalolatnomasining radiatsiya natijasi: radiation_level, radiation_number.
CREATE TABLE calculation_radiation_results (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-14 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-14 … 2026-11-09
    radiation_level float8,
    radiation_number varchar,
    PRIMARY KEY (id)
);

-- TABLE: capa_action  (satrlar: 0 — BO`SH)
CREATE TABLE capa_action (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    action_no integer,
    action_type varchar,
    archived_at timestamptz,
    completed_at timestamptz,
    created_by_user_id varchar,
    description varchar,
    due_at timestamptz,
    effectiveness_comment varchar,
    effectiveness_status varchar,
    effectiveness_verified_at timestamptz,
    effectiveness_verified_by_user_id varchar,
    non_conformance_id varchar NOT NULL,
    responsible_user_id varchar,
    started_at timestamptz,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    title varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (non_conformance_id) REFERENCES non_conformance(id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id)
);

-- TABLE: capa_comment  (satrlar: 0 — BO`SH)
CREATE TABLE capa_comment (
    id varchar NOT NULL,
    author_user_id varchar,
    capa_action_id varchar NOT NULL,
    comment varchar NOT NULL,
    comment_type varchar,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: coal_standards  (satrlar: 10)
-- KO'MIR STANDARTLARI: coal_brand, namlik va kullilik chegaralari. Katta-kichik harfli ustunlar qo'shtirnoqda yoziladi.
CREATE TABLE coal_standards (
    id bigint NOT NULL,
    coal_brand varchar NOT NULL,
    "grainSize" varchar,
    "maxAshContent" float8,  -- kullilikning yuqori chegarasi
    "maxCalorificValue" integer,  -- [har doim NULL — ishlatmang]
    "maxChlorineContent" float8,  -- [har doim NULL — ishlatmang]
    "maxFineFractionAmount" float8,
    "maxMineralImpurities" float8,
    "maxMoisture" float8,  -- namlikning yuqori chegarasi
    "maxSulfurContent" float8,  -- [har doim NULL — ishlatmang]
    "minAshContent" float8,
    "minCalorificValue" integer,
    "minMoisture" float8,
    notes varchar,
    purpose varchar,
    PRIMARY KEY (id)
);

-- TABLE: control_measurement  (satrlar: 3456)
-- NAZORAT O'LCHOVLARI: coalBrand, ashContent, moistureContent, samplingPlace. act_id orqali nazorat dalolatnomasiga bog'langan.
CREATE TABLE control_measurement (
    id bigint NOT NULL,
    "ashContent" float8,
    "checkedByOtk" varchar,  -- [har doim NULL — ishlatmang]
    "coalBrand" varchar,
    "createdAt" timestamp,  -- [har doim NULL — ishlatmang]
    "excavatorNumber" varchar,
    "moistureContent" float8,
    "otkEmployee" varchar,  -- [har doim NULL — ishlatmang]
    "samplingPlace" varchar,
    sequence_number integer,
    "warehouseName" varchar,
    act_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (act_id) REFERENCES acts(id)
);

-- TABLE: core_user  (satrlar: 121)
CREATE TABLE core_user (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-08
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    archived_at timestamptz,  -- oraliq: 2026-11-02 … 2026-11-02
    email varchar,  -- [har doim NULL — ishlatmang]
    full_name varchar NOT NULL,
    is_active boolean NOT NULL,
    last_login_at timestamptz,  -- oraliq: 2026-08-25 … 2026-11-09
    password_hash varchar,  -- [MAXFIY — o'qish taqiqlangan]
    role varchar,  -- RUXSAT: 'ADMIN', 'MANAGER', 'ANALYST', 'REVIEWER', 'USER', 'MASTER_OTK', 'MASTER_EXCAVATOR', 'MASTER_SECTION', 'RADIATION', 'LABORATORY', 'SBIT', 'OTK_NACHALNIK', 'UCHASTKA_NACHALNIK'; BAZADA: 'MASTER_SECTION' 63, 'LABORATORY' 21, 'ADMIN' 8, 'SBIT' 6, 'MASTER_OTK' 5, 'RADIATION' 5, 'ANALYST' 2, 'MASTER_EXCAVATOR' 2, 'OTK_NACHALNIK' 2, 'REVIEWER' 2, 'UCHASTKA_NACHALNIK' 2, 'USER' 2, 'MANAGER' 1
    username varchar,
    workshop_id varchar,  -- [har doim NULL — ishlatmang]
    auth_version bigint,
    role_scope_id varchar,
    role_scope_type varchar,  -- BAZADA: 'GLOBAL' 6
    PRIMARY KEY (id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id)
);

-- TABLE: daily_excavator_work  (satrlar: 336)
-- EKSKAVATOR ISH JURNALI: work_date, shift, excavator_number, uchastnik_id, status. Bitta ekskavator turli sana/smenalarda takrorlanadi. Jurnaldagi alohida ekskavatorlar soni: COUNT(DISTINCT excavator_number).
CREATE TABLE daily_excavator_work (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    "ekskovatorWorkType" varchar,  -- [har doim NULL — ishlatmang]; RUXSAT: 'COAL', 'PRIMARY_KAOLIN', 'SECONDARY_MULTICOLORED', 'SECONDARY_GRAY', 'ROCK_MASS'
    excavator_number varchar NOT NULL,
    shift integer NOT NULL,
    status varchar NOT NULL,  -- BAZADA: 'WORKING' 213, 'INACTIVE' 123
    work_date date NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    excavator_id varchar,
    uchastnik_id varchar NOT NULL,
    works_on_coal boolean,  -- [har doim NULL — ishlatmang]
    ekskovator_work_type varchar,  -- RUXSAT: 'COAL', 'PRIMARY_KAOLIN', 'SECONDARY_MULTICOLORED', 'SECONDARY_GRAY', 'ROCK_MASS'; BAZADA: 'COAL' 304, 'SECONDARY_MULTICOLORED' 16, 'PRIMARY_KAOLIN' 8, 'ROCK_MASS' 8; ISHLATILMAGAN: SECONDARY_GRAY
    PRIMARY KEY (id),
    FOREIGN KEY (uchastnik_id) REFERENCES uchastnik(id),
    FOREIGN KEY (excavator_id) REFERENCES excavators(id)
);

-- TABLE: daily_kaolin_radiations  (satrlar: 50)
-- KAOLIN RADIATSIYA O'LCHOVLARI: entry_date, kaolin_category, effective_activity_class_1.
CREATE TABLE daily_kaolin_radiations (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-26 … 2026-11-04
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-26 … 2026-11-04
    checked_by varchar,
    effective_activity_class_1 integer,
    entry_date date NOT NULL,  -- oraliq: 2026-08-24 … 2026-11-04
    kaolin_category varchar NOT NULL,  -- BAZADA: 'PRIMARY' 33, 'SECONDARY' 17
    PRIMARY KEY (id)
);

-- TABLE: daily_radiations  (satrlar: 196)
-- KUNLIK RADIATSIYA O'LCHOVLARI: entry_date, site_type, radiation_level, radiation_number.
CREATE TABLE daily_radiations (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-25 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-25 … 2026-11-09
    checked_by varchar,
    entry_date date NOT NULL,  -- oraliq: 2026-08-18 … 2026-11-10
    radiation_level float8,
    radiation_number varchar,
    site_type varchar,  -- RUXSAT: 'RAZREZ', 'APARTAK', 'SHAXTA'; BAZADA: 'SHAXTA' 69, 'RAZREZ' 66, 'APARTAK' 61
    PRIMARY KEY (id)
);

-- TABLE: destination_branch_stations  (satrlar: 237)
CREATE TABLE destination_branch_stations (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-10-07 … 2026-11-06
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-10-07 … 2026-11-06
    branch_id varchar NOT NULL,
    station_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (branch_id) REFERENCES destination_branches(id),
    FOREIGN KEY (station_id) REFERENCES destination_stations(id)
);

-- TABLE: destination_branches  (satrlar: 124)
CREATE TABLE destination_branches (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-29 … 2026-11-05
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-29 … 2026-11-05
    name varchar NOT NULL,
    normalized_name varchar NOT NULL,
    code varchar,
    PRIMARY KEY (id)
);

-- TABLE: destination_stations  (satrlar: 248)
CREATE TABLE destination_stations (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-10-04 … 2026-10-26
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-10-07 … 2026-10-26
    name varchar NOT NULL,
    normalized_name varchar NOT NULL,
    code varchar,
    PRIMARY KEY (id)
);

-- TABLE: document_approval  (satrlar: 0 — BO`SH)
CREATE TABLE document_approval (
    id varchar NOT NULL,
    acted_at timestamptz,
    acted_by_user_id varchar,
    approval_order integer NOT NULL,
    approver_user_id varchar,
    comment varchar,
    created_at timestamptz NOT NULL,
    document_id varchar NOT NULL,
    role_code varchar,
    source_step_id varchar,
    source_workflow_id varchar,
    status_code varchar NOT NULL,
    step_name varchar,
    PRIMARY KEY (id)
);

-- TABLE: document_attachment  (satrlar: 0 — BO`SH)
CREATE TABLE document_attachment (
    id varchar NOT NULL,
    attachment_kind varchar NOT NULL,
    content_type varchar NOT NULL,
    created_at timestamptz NOT NULL,
    created_by_user_id varchar,
    document_id varchar NOT NULL,
    file_name varchar NOT NULL,
    file_size integer,
    storage_key varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: document_template  (satrlar: 0 — BO`SH)
CREATE TABLE document_template (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    document_type varchar NOT NULL,
    effective_from timestamptz,
    effective_to timestamptz,
    footer_html varchar,
    header_html varchar,
    is_active boolean NOT NULL,
    is_current boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    renderer_key varchar,
    style_css varchar,
    template_schema_json jsonb,  -- [JSON matn]
    version_label varchar,
    PRIMARY KEY (id)
);

-- TABLE: equipment_usage_event  (satrlar: 0 — BO`SH)
CREATE TABLE equipment_usage_event (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    batch_id varchar,
    comment varchar,
    created_by_user_id varchar,
    instrument_id varchar NOT NULL,
    used_at timestamptz NOT NULL,
    used_count integer NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (created_by_user_id) REFERENCES core_user(id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id)
);

-- TABLE: excavator_coal_brands  (satrlar: 368)
CREATE TABLE excavator_coal_brands (
    daily_excavator_work_id varchar NOT NULL,
    coal_brand varchar,
    FOREIGN KEY (daily_excavator_work_id) REFERENCES daily_excavator_work(id)
);

-- TABLE: excavators  (satrlar: 52)
-- EKSKAVATORLAR ma'lumotnomasi: name, description. Faqat ma'lumotnomadagi son aniq so'ralganda shu jadval sanaladi. Oddiy jami ekskavatorlar soni daily_excavator_work ish jurnalidagi alohida ekskavatorlarni anglatadi.
CREATE TABLE excavators (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-25 … 2026-10-29
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-25 … 2026-10-29
    description varchar,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: gas  (satrlar: 0 — BO`SH)
CREATE TABLE gas (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    is_active boolean NOT NULL,
    code varchar NOT NULL,
    description varchar,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: gornaya_massa_acts  (satrlar: 8)
-- TOG' JINSI MASSASI DALOLATNOMALARI: act_number, act_date, coal_brand, mining_site, total_weight, status.
CREATE TABLE gornaya_massa_acts (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    accountant_name varchar,  -- [har doim NULL — ishlatmang]
    act_date date,  -- oraliq: 2026-11-02 … 2026-11-09
    act_number varchar,
    arbitration_sample_weight float8,  -- [har doim NULL — ishlatmang]
    ash_difference float8,  -- [har doim NULL — ishlatmang]
    banka_number varchar,  -- [har doim NULL — ishlatmang]
    certificate_number varchar,  -- [har doim NULL — ishlatmang]
    chunk_size_actual varchar,
    chunk_size_norm varchar,
    coal_brand varchar,
    departure_station varchar,  -- [har doim NULL — ishlatmang]
    fine_fraction_actual float8,  -- [har doim NULL — ishlatmang]
    fine_fraction_norm float8,  -- [har doim NULL — ishlatmang]
    gost_sample varchar,  -- [har doim NULL — ishlatmang]
    lab_sample_weight float8,  -- [har doim NULL — ishlatmang]
    master_otk_checked_by varchar,  -- [har doim NULL — ishlatmang]
    master_otk_name varchar,  -- [har doim NULL — ishlatmang]
    master_section_name varchar,
    max_moisture_norm float8,  -- [har doim NULL — ishlatmang]
    min_ash_norm float8,  -- [har doim NULL — ishlatmang]
    mineral_impurities_actual float8,
    mineral_impurities_norm float8,  -- [har doim NULL — ishlatmang]
    mining_site varchar,
    moisture_difference float8,  -- [har doim NULL — ishlatmang]
    party_number varchar,  -- [har doim NULL — ishlatmang]
    party_volume float8,
    seal_number varchar,  -- [har doim NULL — ishlatmang]
    shipment_date_period varchar,  -- [har doim NULL — ishlatmang]
    standard_name varchar,
    status varchar,  -- BAZADA: 'OTK_GA_YUBORILDI' 8
    surcharge_or_discount_per_ton float8,  -- [har doim NULL — ishlatmang]
    surcharge_or_discount_percent float8,  -- [har doim NULL — ishlatmang]
    total_wagons integer,
    total_weight float8,
    uchastka_checked_by varchar,
    visible_impurities_actual float8,  -- [har doim NULL — ishlatmang]
    wagon_received_date date,  -- oraliq: 2026-11-02 … 2026-11-09
    zbit_checked_by varchar,  -- [har doim NULL — ishlatmang]
    gornaya_brand varchar,
    product_name varchar,
    radiation_checked_by varchar,
    radiation_level float8,
    radiation_number varchar,
    max_ash_norm float8,  -- [har doim NULL — ishlatmang]
    PRIMARY KEY (id)
);

-- TABLE: gornaya_massa_wagons  (satrlar: 8)
-- Tog' jinsi massasi dalolatnomasidagi vagonlar: wagon_number, weight, dispatch_date, gornaya_massa_act_id.
CREATE TABLE gornaya_massa_wagons (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    consumer_name varchar,  -- [har doim NULL — ishlatmang]
    destination_station varchar,  -- [har doim NULL — ishlatmang]
    dispatch_date date,  -- oraliq: 2026-11-02 … 2026-11-09
    wagon_number varchar,
    weight float8,
    gornaya_massa_act_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (gornaya_massa_act_id) REFERENCES gornaya_massa_acts(id)
);

-- TABLE: instrument  (satrlar: 0 — BO`SH)
CREATE TABLE instrument (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    accuracy_class varchar,
    archived_at timestamptz,
    asset_tag varchar,
    blocked_reason varchar,
    calibration_due_at timestamptz,
    code varchar NOT NULL,
    current_usage_count integer NOT NULL,
    expired_date timestamptz,
    instrument_type varchar,  -- RUXSAT: 'GC', 'SPECTROMETER'
    is_active boolean NOT NULL,
    lab_id varchar NOT NULL,
    last_calibration_at timestamptz,
    last_maintenance_at timestamptz,
    last_qualification_at timestamptz,
    location varchar,
    maintenance_due_at timestamptz,
    manufacturer varchar,
    max_usage_count integer,
    measurement_range varchar,
    measurement_unit varchar,
    metrology_state varchar,
    model varchar,
    name varchar NOT NULL,
    parent_instrument_id varchar,
    plant_id varchar NOT NULL,
    qualification_due_at timestamptz,
    serial_number varchar,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    verification_interval_months integer,
    verification_mode varchar,
    verification_provider varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (lab_id) REFERENCES lab(id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id),
    FOREIGN KEY (parent_instrument_id) REFERENCES instrument(id)
);

-- TABLE: instrument_calibration  (satrlar: 0 — BO`SH)
CREATE TABLE instrument_calibration (
    id varchar NOT NULL,
    calibration_date timestamptz,
    certificate_no varchar,
    comment varchar,
    created_at timestamptz,
    created_by_user_id varchar,
    due_at timestamptz,
    instrument_id varchar NOT NULL,
    outcome_code varchar,
    performed_by varchar,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: instrument_calibration_attachment  (satrlar: 0 — BO`SH)
CREATE TABLE instrument_calibration_attachment (
    id varchar NOT NULL,
    attachment_kind varchar NOT NULL,
    calibration_id varchar NOT NULL,
    comment varchar,
    content_type varchar,
    file_name varchar NOT NULL,
    file_size integer,
    instrument_id varchar NOT NULL,
    plant_id varchar NOT NULL,
    storage_key varchar NOT NULL,
    uploaded_at timestamptz NOT NULL,
    uploaded_by_user_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: instrument_maintenance  (satrlar: 0 — BO`SH)
CREATE TABLE instrument_maintenance (
    id varchar NOT NULL,
    comment varchar,
    completed_at timestamptz,
    created_at timestamptz,
    created_by_user_id varchar,
    instrument_id varchar NOT NULL,
    maintenance_type varchar,
    next_due_at timestamptz,
    performed_by varchar,
    plant_id varchar NOT NULL,
    scheduled_at timestamptz,
    started_at timestamptz,
    PRIMARY KEY (id)
);

-- TABLE: instrument_metrology_schedule  (satrlar: 0 — BO`SH)
CREATE TABLE instrument_metrology_schedule (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    actual_calibration_id varchar,
    actual_qualification_id varchar,
    comment varchar,
    estimated_cost numeric(38,2),
    instrument_id varchar NOT NULL,
    last_verified_at date,
    planned_month integer NOT NULL,
    planned_provider varchar,
    plant_id varchar NOT NULL,
    schedule_type varchar NOT NULL,
    schedule_year integer NOT NULL,
    verification_interval_months integer,
    PRIMARY KEY (id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id),
    FOREIGN KEY (actual_qualification_id) REFERENCES instrument_qualification(id),
    FOREIGN KEY (actual_calibration_id) REFERENCES instrument_calibration(id)
);

-- TABLE: instrument_qualification  (satrlar: 0 — BO`SH)
CREATE TABLE instrument_qualification (
    id varchar NOT NULL,
    comment varchar,
    created_at timestamptz,
    created_by_user_id varchar,
    due_at timestamptz,
    instrument_id varchar NOT NULL,
    plant_id varchar NOT NULL,
    protocol_no varchar,
    qualification_type varchar,
    qualified_at timestamptz,
    PRIMARY KEY (id)
);

-- TABLE: integration_delivery  (satrlar: 0 — BO`SH)
CREATE TABLE integration_delivery (
    id varchar NOT NULL,
    attempted_at timestamptz,
    created_at timestamptz,
    duration_ms integer,
    endpoint_id varchar,
    error_message varchar,
    event_id varchar,
    http_status integer,
    plant_id varchar,
    request_payload_json jsonb,  -- [JSON matn]
    response_payload_json jsonb,  -- [JSON matn]
    status varchar,
    PRIMARY KEY (id)
);

-- TABLE: integration_endpoint  (satrlar: 0 — BO`SH)
CREATE TABLE integration_endpoint (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    adapter_key varchar,
    archived_at timestamptz,
    auth_type varchar,
    base_url varchar,
    code varchar NOT NULL,
    config_json jsonb,  -- [JSON matn]
    direction varchar NOT NULL,
    last_error_at timestamptz,
    last_heartbeat_at timestamptz,
    last_success_at timestamptz,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    status varchar NOT NULL,
    supports_retry boolean,
    system_code varchar NOT NULL,
    transport_kind varchar,
    PRIMARY KEY (id)
);

-- TABLE: integration_event  (satrlar: 0 — BO`SH)
CREATE TABLE integration_event (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    attempt_count integer,
    correlation_key varchar,
    created_by_user_id varchar,
    direction varchar NOT NULL,
    dispatched_at timestamptz,
    endpoint_id varchar NOT NULL,
    entity_id varchar NOT NULL,
    entity_type varchar NOT NULL,
    error_message varchar,
    last_attempt_at timestamptz,
    next_retry_at timestamptz,
    payload_json jsonb,  -- [JSON matn]
    plant_id varchar NOT NULL,
    queued_at timestamptz,
    response_json jsonb,  -- [JSON matn]
    source_system varchar,
    status varchar NOT NULL,
    topic varchar,
    PRIMARY KEY (id)
);

-- TABLE: kaolin_certificate_railcars  (satrlar: 223)
CREATE TABLE kaolin_certificate_railcars (
    kaolin_certificate_id bigint NOT NULL,
    railcar_number varchar,
    weight float8,
    FOREIGN KEY (kaolin_certificate_id) REFERENCES kaolin_certificates(id)
);

-- TABLE: kaolin_certificates  (satrlar: 36)
CREATE TABLE kaolin_certificates (
    id bigint NOT NULL,
    active boolean NOT NULL,
    al2o3_percent float8,
    batch_weight float8,
    consumer varchar,
    created_at timestamp,  -- oraliq: 2026-09-06 … 2026-10-13
    destination_station varchar,
    effective_activity_class_1 integer,
    fe2o3_percent float8,
    head_brb varchar,
    kaolin_type varchar,  -- BAZADA: 'Birlamchi kaolin' 35, 'Ikkilamchi rang-barang kaolin' 1
    lab_issue_date date,  -- oraliq: 2026-06-03 … 2026-10-09
    lab_name varchar,
    organization varchar,
    otk_inspector varchar,
    ppp_percent float8,
    radiation_name varchar,
    railcar_numbers varchar,
    shipping_date date,  -- oraliq: 2026-09-06 … 2026-10-13
    sio2_percent float8,
    status varchar,  -- RUXSAT: 'CREATED', 'SENT_TO_OTK', 'OTK_APPROVED', 'SENT_TO_RADIATION', 'RADIATION_APPROVED', 'SENT_TO_ZBIT', 'ZBIT_APPROVED', 'COMPLETED'; BAZADA: 'SENT_TO_ZBIT' 16, 'SENT_TO_OTK' 15, 'COMPLETED' 4, 'CREATED' 1; ISHLATILMAGAN: OTK_APPROVED, SENT_TO_RADIATION, RADIATION_APPROVED, ZBIT_APPROVED
    storage_conditions varchar,
    technical_conditions varchar,
    uchastnik_master_name varchar,
    w_percent float8,
    party_number varchar,
    sent_to_otk_at timestamp,  -- oraliq: 2026-09-11 … 2026-10-13
    PRIMARY KEY (id)
);

-- TABLE: lab  (satrlar: 1)
-- LABORATORIYALAR ma'lumotnomasi: code, name, lab_type, is_active.
CREATE TABLE lab (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    archived_at timestamptz,  -- [har doim NULL — ishlatmang]
    code varchar NOT NULL,  -- BAZADA: 'CENTRAL_LAB' 1
    is_active boolean NOT NULL,
    lab_type varchar,  -- [har doim NULL — ishlatmang]
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: lab_result  (satrlar: 0 — BO`SH)
-- QISQA LABORATORIYA NATIJALARI: partiya_raqami, result_date, namlik_wa, kullilik_ad, material_type. O'chirilmagan yozuvlar: deleted IS NOT TRUE.
CREATE TABLE lab_result (
    id bigint NOT NULL,
    "createdAt" timestamp,
    deleted boolean NOT NULL,
    "updatedAt" timestamp,
    exported boolean,
    kullilik_ad numeric(6,2),
    material_type varchar NOT NULL,  -- RUXSAT: 'KOMIR', 'GORNAYA_MASSA', 'BIRLAMCHI_KAOLIN', 'IKKILAMCHI_KULRANG', 'IKKILAMCHI_RANGLI'
    namlik_wa numeric(6,2) NOT NULL,
    partiya_raqami varchar NOT NULL,
    result_date date NOT NULL,
    kaolin_type varchar,  -- RUXSAT: 'PRIMARY_KAOLIN', 'SECONDARY_MULTICOLORED', 'SECONDARY_GRAY'
    coal_brand varchar,
    PRIMARY KEY (id)
);

-- TABLE: laboratory_results  (satrlar: 4464)
-- KO'MIR LABORATORIYA NATIJALARI: namlik moisture_content, kullilik ash_content, standartga moslik passed_standard. Sana test_date_time; uchastka uchastka_id. workflow_type va FK lar natija qaysi dalolatnomaga tegishli ekanini bildiradi.
CREATE TABLE laboratory_results (
    id bigint NOT NULL,
    allowed_tolerance float8,  -- [har doim NULL — ishlatmang]
    analytical_moisture float8,  -- [har doim NULL — ishlatmang]
    ash_container_1 varchar,  -- [har doim NULL — ishlatmang]
    ash_container_2 varchar,  -- [har doim NULL — ishlatmang]
    ash_container_3 varchar,  -- [har doim NULL — ishlatmang]
    ash_content float8,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    final_result float8,
    lab_checked_by varchar,
    lab_role varchar,  -- [har doim NULL — ishlatmang]
    lab_technician varchar,
    moisture_1_m1 float8,  -- [har doim NULL — ishlatmang]
    moisture_1_m2 float8,  -- [har doim NULL — ishlatmang]
    moisture_1_m3 float8,  -- [har doim NULL — ishlatmang]
    moisture_2_m1 float8,  -- [har doim NULL — ishlatmang]
    moisture_2_m2 float8,  -- [har doim NULL — ishlatmang]
    moisture_2_m3 float8,  -- [har doim NULL — ishlatmang]
    moisture_3_m1 float8,  -- [har doim NULL — ishlatmang]
    moisture_3_m2 float8,  -- [har doim NULL — ishlatmang]
    moisture_3_m3 float8,  -- [har doim NULL — ishlatmang]
    moisture_container_1 varchar,  -- [har doim NULL — ishlatmang]
    moisture_container_2 varchar,  -- [har doim NULL — ishlatmang]
    moisture_container_3 varchar,  -- [har doim NULL — ishlatmang]
    moisture_content float8,
    moisture_difference float8,  -- [har doim NULL — ishlatmang]
    passed_standard boolean,  -- true = standartga mos; false = mos emas; NULL = baho noma'lum
    quality_reason text,
    quality_status varchar,  -- BAZADA: 'PASSED' 84, 'FAILED' 13
    sequence_number bigint NOT NULL,
    test_date_time timestamp,  -- laboratoriya tekshiruvining ish vaqti; oraliq: 2026-09-06 … 2026-11-09
    tolerance_category varchar,  -- [har doim NULL — ishlatmang]
    tolerance_reason text,  -- [har doim NULL — ishlatmang]
    tolerance_status varchar,  -- BAZADA: 'MANUAL' 2931, 'MANUAL_UPDATE' 98
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    workflow_type varchar NOT NULL,  -- RUXSAT: 'CONTROL_ACT', 'CALCULATION', 'TRUCK_CALCULATION', 'GORNAYA_MASSA'; BAZADA: 'CONTROL_ACT' 3456, 'CALCULATION' 1008; ISHLATILMAGAN: TRUCK_CALCULATION, GORNAYA_MASSA
    calculation_act_id varchar,
    measurement_id bigint,
    truck_calculation_act_id varchar,
    uchastka_id varchar,
    gornaya_massa_act_id varchar,  -- [har doim NULL — ishlatmang]
    PRIMARY KEY (id),
    FOREIGN KEY (calculation_act_id) REFERENCES calculation_acts(id),
    FOREIGN KEY (gornaya_massa_act_id) REFERENCES gornaya_massa_acts(id),
    FOREIGN KEY (truck_calculation_act_id) REFERENCES truck_calculation_acts(id),
    FOREIGN KEY (measurement_id) REFERENCES control_measurement(id),
    FOREIGN KEY (uchastka_id) REFERENCES uchastnik(id)
);

-- TABLE: material  (satrlar: 0 — BO`SH)
CREATE TABLE material (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: method  (satrlar: 0 — BO`SH)
CREATE TABLE method (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    lab_id varchar NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    purpose varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (lab_id) REFERENCES lab(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: method_reagent_norm  (satrlar: 0 — BO`SH)
CREATE TABLE method_reagent_norm (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    comment varchar,
    method_version_id varchar NOT NULL,
    quantity numeric(38,2) NOT NULL,
    reagent_id varchar NOT NULL,
    unit_of_measure_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: method_version  (satrlar: 0 — BO`SH)
CREATE TABLE method_version (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    calculation_formula varchar,
    change_summary varchar,
    created_by_user_id varchar,
    effective_from timestamptz,
    effective_to timestamptz,
    is_current boolean,
    lifecycle_status varchar,
    method_id varchar NOT NULL,
    precautions_text varchar,
    procedure_text varchar,
    version_code varchar,
    version_no integer,
    PRIMARY KEY (id)
);

-- TABLE: non_conformance  (satrlar: 0 — BO`SH)
CREATE TABLE non_conformance (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    assigned_to_user_id varchar,
    batch_id varchar,
    closed_at timestamptz,
    containment_action varchar,
    description varchar NOT NULL,
    detected_by_user_id varchar,
    due_at timestamptz,
    identified_at timestamptz NOT NULL,
    linked_instrument_id varchar,
    linked_method_version_id varchar,
    linked_reagent_lot_id varchar,
    nc_no varchar NOT NULL,
    plant_id varchar NOT NULL,
    quality_decision_id varchar,
    result_id varchar,
    root_cause varchar,
    sample_id varchar,
    severity_code varchar NOT NULL,
    source_code varchar,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    title varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (sample_id) REFERENCES sample(id),
    FOREIGN KEY (batch_id) REFERENCES batch(id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id)
);

-- TABLE: normative_document  (satrlar: 0 — BO`SH)
CREATE TABLE normative_document (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    amendment_info varchar,
    approval_authority varchar,
    approval_date date,
    approval_document_no varchar,
    archived_at timestamptz,
    attestation_status varchar,
    code varchar NOT NULL,
    document_family varchar NOT NULL,
    effective_from date,
    effective_to date,
    is_active boolean NOT NULL,
    lab_id varchar,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    registry_no varchar,
    related_document_id varchar,
    related_document_relation_type varchar,
    source_review_note varchar,
    source_review_status varchar,
    source_url varchar,
    valid_until date,
    version_label varchar,
    version_status varchar,
    workshop_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id),
    FOREIGN KEY (lab_id) REFERENCES lab(id)
);

-- TABLE: normative_document_attachment  (satrlar: 0 — BO`SH)
CREATE TABLE normative_document_attachment (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    attachment_type varchar NOT NULL,
    comment varchar,
    mime_type varchar,
    normative_document_id varchar NOT NULL,
    plant_id varchar NOT NULL,
    source_url varchar NOT NULL,
    title varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: normative_document_link  (satrlar: 0 — BO`SH)
CREATE TABLE normative_document_link (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    comment varchar,
    normative_document_id varchar NOT NULL,
    plant_id varchar NOT NULL,
    relation_type varchar NOT NULL,
    target_id varchar NOT NULL,
    target_type varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: notifications  (satrlar: 6990)
CREATE TABLE notifications (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-12 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-12 … 2026-11-09
    is_read boolean,
    message varchar NOT NULL,
    recipient_role varchar NOT NULL,  -- BAZADA: 'LABORATORY' 2511, 'SECTION_MASTER' 1438, 'MASTER_OTK' 1095, 'RADIATION' 1072, 'SBIT' 866, 'MASTER_SECTION' 8
    reference_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: otk_registry_entry  (satrlar: 0 — BO`SH)
CREATE TABLE otk_registry_entry (
    id bigint NOT NULL,
    "createdAt" timestamp,
    deleted boolean NOT NULL,
    "updatedAt" timestamp,
    firma_nomi varchar NOT NULL,
    linked_to_akt boolean,
    registry_date date NOT NULL,
    source_ref varchar NOT NULL,
    umumiy_ogirlik_tonna numeric(12,3) NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: permission  (satrlar: 87)
CREATE TABLE permission (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-10-24
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-10-24
    action_key varchar,  -- [har doim NULL — ishlatmang]
    code varchar NOT NULL,
    description varchar,
    module_key varchar,  -- [har doim NULL — ishlatmang]
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: plant  (satrlar: 1)
CREATE TABLE plant (
    id varchar NOT NULL,
    code varchar NOT NULL,  -- BAZADA: 'NAVOIYAZOT' 1
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: priority  (satrlar: 0 — BO`SH)
CREATE TABLE priority (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    color varchar,
    is_active boolean NOT NULL,
    is_default boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    sort_order integer NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: product  (satrlar: 0 — BO`SH)
CREATE TABLE product (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    workshop_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id)
);

-- TABLE: product_calculation_definition  (satrlar: 3)
CREATE TABLE product_calculation_definition (
    id varchar NOT NULL,
    product_id varchar NOT NULL,
    product_code varchar NOT NULL,
    product_name varchar,
    source_code varchar,
    source_name varchar,
    version varchar NOT NULL,
    grades_json text,  -- [JSON matn]
    is_active boolean NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_calculation_field  (satrlar: 42)
CREATE TABLE product_calculation_field (
    id varchar NOT NULL,
    definition_id varchar NOT NULL,
    name varchar NOT NULL,
    label varchar NOT NULL,
    field_type varchar NOT NULL,  -- BAZADA: 'NUMBER' 41, 'TEXT' 1
    section_key varchar,
    unit_label varchar,  -- BAZADA: 'g' 11, '%' 6, 'ml' 6, 'kgf' 1, 'kg/m3' 1, 'mg/l' 1
    is_required boolean NOT NULL,
    validation_json text,  -- [JSON matn]
    default_value_json text,  -- [JSON matn]
    sort_order integer NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_calculation_metric  (satrlar: 14)
CREATE TABLE product_calculation_metric (
    id varchar NOT NULL,
    definition_id varchar NOT NULL,
    metric_key varchar NOT NULL,
    title varchar NOT NULL,
    expression text,
    unit_label varchar,  -- BAZADA: '%' 10, '' 1, 'kgf' 1, 'kg/m3' 1, 'mg/l' 1
    norm_type varchar,  -- BAZADA: 'MAX' 6, 'MIN' 6, 'RANGE' 1, 'UNKNOWN' 1
    norms_json text,  -- [JSON matn]
    sort_order integer NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_equipment_requirement  (satrlar: 0 — BO`SH)
CREATE TABLE product_equipment_requirement (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    instrument_id varchar NOT NULL,
    is_required boolean NOT NULL,
    notes varchar,
    production_profile_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (production_profile_id) REFERENCES product_production_profile(id),
    FOREIGN KEY (instrument_id) REFERENCES instrument(id)
);

-- TABLE: product_material_requirement  (satrlar: 0 — BO`SH)
CREATE TABLE product_material_requirement (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    is_required boolean NOT NULL,
    material_id varchar NOT NULL,
    max_value numeric(18,6),
    min_value numeric(18,6),
    notes varchar,
    production_profile_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (production_profile_id) REFERENCES product_production_profile(id),
    FOREIGN KEY (material_id) REFERENCES material(id)
);

-- TABLE: product_production_profile  (satrlar: 0 — BO`SH)
CREATE TABLE product_production_profile (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    description varchar,
    is_active boolean NOT NULL,
    product_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES product(id)
);

-- TABLE: product_quality_calculation_result  (satrlar: 0 — BO`SH)
-- MAHSULOT SIFAT HISOBLASH NATIJALARI: product_code, source_code, grade, batch_id, sample_id, status; inputs_json va result_json matn ko'rinishidagi JSON.
CREATE TABLE product_quality_calculation_result (
    id varchar NOT NULL,
    product_code varchar NOT NULL,
    source_code varchar NOT NULL,
    grade varchar,
    batch_id varchar,
    sample_id varchar,
    analyst_full_name varchar,
    inputs_json text,  -- [JSON matn]
    normalized_inputs_json text,  -- [JSON matn]
    result_json text,  -- [JSON matn]
    status varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: product_quality_catalog  (satrlar: 1)
CREATE TABLE product_quality_catalog (
    id varchar NOT NULL,
    product_code varchar NOT NULL,
    product_name varchar NOT NULL,
    version varchar NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    PRIMARY KEY (id)
);

-- TABLE: product_quality_check  (satrlar: 105)
CREATE TABLE product_quality_check (
    id varchar NOT NULL,
    source_id varchar NOT NULL,
    check_code varchar NOT NULL,
    method_code varchar,
    component varchar NOT NULL,
    unit_label varchar,  -- BAZADA: '%' 65, 'mg/l' 24, 'µS/cm' 5, 'mg/m3' 2, 'g/сm3' 1, 'kgf' 1, 'kg/m3' 1, 'сР' 1
    norm_text varchar,
    norm_type varchar,  -- BAZADA: 'MAX' 80, 'RANGE' 17, 'MIN' 6, 'UNKNOWN' 1
    norm_min numeric(18,6),
    norm_max numeric(18,6),
    metric_key varchar,
    calculation_enabled boolean NOT NULL,
    sort_order integer NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_quality_resource  (satrlar: 24)
CREATE TABLE product_quality_resource (
    id varchar NOT NULL,
    catalog_id varchar NOT NULL,
    source_id varchar,  -- [har doim NULL — ishlatmang]
    resource_code varchar NOT NULL,
    resource_type varchar NOT NULL,  -- BAZADA: 'EQUIPMENT' 7, 'REAGENT' 6, 'AUXILIARY_EQUIPMENT' 5, 'RAW_MATERIAL' 5, 'REACTIVE_GAS' 1
    name varchar NOT NULL,
    description varchar,
    sort_order integer NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_quality_source  (satrlar: 26)
CREATE TABLE product_quality_source (
    id varchar NOT NULL,
    catalog_id varchar NOT NULL,
    source_code varchar NOT NULL,
    source_name varchar NOT NULL,
    equipment_code varchar,
    sample_points_json text,  -- [JSON matn]
    sort_order integer NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-09 … 2026-11-09
    PRIMARY KEY (id)
);

-- TABLE: product_standards  (satrlar: 0 — BO`SH)
CREATE TABLE product_standards (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    description varchar,
    is_active boolean,
    max_value bigint,
    metric_key varchar,
    min_value bigint,
    product_id varchar,
    unit_label varchar,
    PRIMARY KEY (id)
);

-- TABLE: production_batch  (satrlar: 0 — BO`SH)
CREATE TABLE production_batch (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    batch_number varchar NOT NULL,
    completed_at timestamptz,
    completed_by varchar,
    completion_notes varchar,
    end_time timestamptz,
    notes varchar,
    product_id varchar NOT NULL,
    production_profile_id varchar NOT NULL,
    start_time timestamptz,
    status varchar NOT NULL,  -- RUXSAT: 'CREATED', 'READY', 'IN_PRODUCTION', 'COMPLETED', 'RELEASED', 'BLOCKED'
    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (production_profile_id) REFERENCES product_production_profile(id)
);

-- TABLE: production_batch_readiness_snapshot  (satrlar: 0 — BO`SH)
CREATE TABLE production_batch_readiness_snapshot (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    batch_id varchar NOT NULL,
    calculated_at timestamptz NOT NULL,
    readiness_json text NOT NULL,  -- [JSON matn]
    ready boolean NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id)
);

-- TABLE: production_batch_release  (satrlar: 0 — BO`SH)
CREATE TABLE production_batch_release (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    batch_id varchar NOT NULL,
    release_comment varchar,
    released_at timestamptz NOT NULL,
    released_by varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id)
);

-- TABLE: production_batch_start_audit  (satrlar: 0 — BO`SH)
CREATE TABLE production_batch_start_audit (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    batch_id varchar NOT NULL,
    readiness_snapshot_id varchar NOT NULL,
    result_status varchar NOT NULL,
    started_at timestamptz NOT NULL,
    started_by varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (readiness_snapshot_id) REFERENCES production_batch_readiness_snapshot(id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id)
);

-- TABLE: production_deviation  (satrlar: 0 — BO`SH)
CREATE TABLE production_deviation (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    analysis_code varchar NOT NULL,
    analysis_id varchar NOT NULL,
    batch_id varchar NOT NULL,
    corrective_action varchar,
    created_by varchar,
    description varchar,
    detected_at timestamptz NOT NULL,
    detected_value varchar,
    expected_value varchar,
    preventive_action varchar,
    product_id varchar NOT NULL,
    resolved_at timestamptz,
    resolved_by varchar,
    root_cause varchar,
    severity varchar NOT NULL,  -- RUXSAT: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    source_code varchar NOT NULL,
    status varchar NOT NULL,  -- RUXSAT: 'OPEN', 'INVESTIGATING', 'RESOLVED', 'CLOSED'
    title varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (created_by) REFERENCES core_user(id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id),
    FOREIGN KEY (resolved_by) REFERENCES core_user(id),
    FOREIGN KEY (analysis_id) REFERENCES production_raw_material_analysis(id)
);

-- TABLE: production_import_session  (satrlar: 0 — BO`SH)
CREATE TABLE production_import_session (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    failed_rows integer NOT NULL,
    file_name varchar NOT NULL,
    finished_at timestamptz,
    imported_by varchar,
    product_code varchar NOT NULL,
    started_at timestamptz NOT NULL,
    status varchar NOT NULL,  -- RUXSAT: 'UPLOADED', 'VALIDATING', 'VALIDATED', 'IMPORTING', 'COMPLETED', 'FAILED'
    success_rows integer NOT NULL,
    total_rows integer NOT NULL,
    validation_errors_json text,  -- [JSON matn]
    PRIMARY KEY (id)
);

-- TABLE: production_raw_material_analysis  (satrlar: 0 — BO`SH)
CREATE TABLE production_raw_material_analysis (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    analyst_id varchar,
    approval_status varchar NOT NULL,  -- RUXSAT: 'PENDING', 'APPROVED', 'REJECTED'
    approved_at timestamptz,
    approved_by varchar,
    batch_id varchar NOT NULL,
    calculated_at timestamptz,
    calculation_status varchar NOT NULL,  -- RUXSAT: 'DRAFT', 'CALCULATED', 'NORMA', 'CHETLANISH'
    checked_at timestamptz,
    inputs_json text,  -- [JSON matn]
    product_id varchar NOT NULL,
    raw_material_code varchar NOT NULL,
    raw_material_name varchar NOT NULL,
    result_json text,  -- [JSON matn]
    source_code varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (approved_by) REFERENCES core_user(id),
    FOREIGN KEY (analyst_id) REFERENCES core_user(id),
    FOREIGN KEY (batch_id) REFERENCES production_batch(id),
    FOREIGN KEY (product_id) REFERENCES product(id)
);

-- TABLE: quality_decision  (satrlar: 0 — BO`SH)
CREATE TABLE quality_decision (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    batch_id varchar,
    comment varchar,
    decided_at timestamptz,
    decided_by_user_id varchar,
    decision_no varchar NOT NULL,
    effective_at timestamptz,
    hold_until timestamptz,
    plant_id varchar NOT NULL,
    reason_code varchar,
    result_id varchar,
    sample_id varchar,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    PRIMARY KEY (id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id)
);

-- TABLE: quality_document  (satrlar: 0 — BO`SH)
CREATE TABLE quality_document (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    approved_at timestamptz,
    archived_at timestamptz,
    batch_id varchar,
    checksum varchar,
    document_no varchar NOT NULL,
    document_type varchar NOT NULL,
    issued_at timestamptz,
    issued_by_user_id varchar,
    lifecycle_status varchar NOT NULL,
    plant_id varchar NOT NULL,
    previous_revision_id varchar,
    quality_decision_id varchar,
    rendered_html text,  -- [MAXFIY — o'qish taqiqlangan]
    result_id varchar,
    revision_no integer,
    sample_id varchar,
    snapshot_json jsonb,  -- [JSON matn]
    superseded_by_document_id varchar,
    template_id varchar,
    title varchar,
    void_reason varchar,
    voided_at timestamptz,
    voided_by_user_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: radiation_spravka  (satrlar: 0 — BO`SH)
-- RADIATSIYA MA'LUMOTNOMALARI: startDate, endDate, branchName, status.
CREATE TABLE radiation_spravka (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    "branchName" varchar,
    "creatorFullName" varchar,
    "endDate" date,
    "startDate" date,
    status varchar,  -- RUXSAT: 'CREATED', 'SENT_TO_OTK', 'OTK_ACCEPTED'
    "otkAcceptorFullName" varchar,
    PRIMARY KEY (id)
);

-- TABLE: radiation_spravka_items  (satrlar: 0 — BO`SH)
-- Radiatsiya ma'lumotnomasi o'lchovlari: createdAt, radiationLevel, spravka_id.
CREATE TABLE radiation_spravka_items (
    id bigint NOT NULL,
    "createdAt" date,
    "radiationLevel" float8,
    spravka_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (spravka_id) REFERENCES radiation_spravka(id)
);

-- TABLE: reagent  (satrlar: 0 — BO`SH)
CREATE TABLE reagent (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    category varchar,
    code varchar NOT NULL,
    default_shelf_life_days integer,
    grade varchar,
    is_active boolean NOT NULL,
    min_stock_level numeric(38,2),
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    storage_condition varchar,
    unit_of_measure_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: reagent_consumption  (satrlar: 0 — BO`SH)
CREATE TABLE reagent_consumption (
    id varchar NOT NULL,
    comment varchar,
    consumed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL,
    created_by_user_id varchar,
    plant_id varchar NOT NULL,
    quantity numeric(38,2) NOT NULL,
    reagent_id varchar NOT NULL,
    reagent_lot_id varchar NOT NULL,
    reason_code varchar,
    result_id varchar,
    sample_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: reagent_lot  (satrlar: 0 — BO`SH)
CREATE TABLE reagent_lot (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    available_quantity numeric(38,2),
    certificate_no varchar,
    comment varchar,
    created_by_user_id varchar,
    expires_at timestamptz,
    initial_quantity numeric(38,2),
    lot_no varchar NOT NULL,
    manufactured_at timestamptz,
    opened_at timestamptz,
    plant_id varchar NOT NULL,
    reagent_id varchar NOT NULL,
    received_at timestamptz,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    storage_location varchar,
    supplier_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id),
    FOREIGN KEY (reagent_id) REFERENCES reagent(id)
);

-- TABLE: reject_reason  (satrlar: 0 — BO`SH)
CREATE TABLE reject_reason (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    category varchar,
    code varchar NOT NULL,
    description varchar,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: result  (satrlar: 0 — BO`SH)
CREATE TABLE result (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    approved_at timestamptz,
    approved_by_user_id varchar,
    archived_at timestamptz,
    comment varchar,
    evaluation_code varchar,
    instrument_code varchar,
    instrument_name varchar,
    is_out_of_spec boolean,
    method_version_id varchar,
    numeric_value numeric(38,2),
    operator_user_id varchar,
    specification_item_id varchar,
    status_id varchar,
    submitted_at timestamptz,
    submitted_by_user_id varchar,
    test_order_id varchar NOT NULL,
    text_value varchar,
    value_type varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (test_order_id) REFERENCES test_order(id)
);

-- TABLE: result_measurement  (satrlar: 0 — BO`SH)
CREATE TABLE result_measurement (
    id varchar NOT NULL,
    captured_at timestamptz,
    comment varchar,
    measurement_no integer,
    numeric_value numeric(38,2),
    result_id varchar,
    text_value varchar,
    PRIMARY KEY (id)
);

-- TABLE: result_revision  (satrlar: 0 — BO`SH)
CREATE TABLE result_revision (
    id varchar NOT NULL,
    action_code varchar,
    actor_user_id varchar,
    comment varchar,
    created_at timestamptz,
    new_value_json jsonb,  -- [JSON matn]
    old_value_json jsonb,  -- [JSON matn]
    result_id varchar,
    revision_no integer,
    PRIMARY KEY (id)
);

-- TABLE: role  (satrlar: 14)
CREATE TABLE role (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-09-02
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-09-02
    archived_at timestamptz,  -- [har doim NULL — ishlatmang]
    code varchar NOT NULL,  -- BAZADA: 'Administrator' 1, 'Chemist' 1, 'LabManager' 1, 'LABORATORY' 1, 'MASTER_EXCAVATOR' 1, 'MASTER_OTK' 1, 'MASTER_SECTION' 1, 'Metrology' 1, 'OTK_NACHALNIK' 1, 'QualityControl' 1, 'RADIATION' 1, 'SBIT' 1, 'UCHASTKA_NACHALNIK' 1, 'Warehouse' 1
    description varchar,
    is_system boolean NOT NULL,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: role_permission  (satrlar: 416)
CREATE TABLE role_permission (
    id varchar NOT NULL,
    created_at timestamptz,  -- oraliq: 2026-08-08 … 2026-10-28
    permission_id varchar,
    role_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: sample  (satrlar: 0 — BO`SH)
CREATE TABLE sample (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    batch_id varchar,
    collected_by_user_id varchar,
    control_type varchar NOT NULL,
    description varchar,
    disposal_note varchar,
    disposed_at timestamptz,
    disposed_by_user_id varchar,
    due_at timestamptz,
    external_ref varchar,
    lab_id varchar NOT NULL,
    label_code varchar,
    label_printed_at timestamptz,
    material_id varchar,
    plant_id varchar NOT NULL,
    priority_id varchar NOT NULL,
    product_id varchar,
    received_at timestamptz NOT NULL,
    registered_by_user_id varchar,
    retention_note varchar,
    retention_until timestamptz,
    sample_no varchar NOT NULL,
    sample_source_id varchar NOT NULL,
    sample_type_id varchar NOT NULL,
    sampling_point_id varchar,
    section_id varchar,
    shift_id varchar,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    storage_condition varchar,
    storage_location varchar,
    storage_location_id varchar,
    supplier_id varchar,
    taken_at timestamptz NOT NULL,
    workshop_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (sample_type_id) REFERENCES sample_type(id),
    FOREIGN KEY (priority_id) REFERENCES priority(id),
    FOREIGN KEY (batch_id) REFERENCES batch(id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id),
    FOREIGN KEY (lab_id) REFERENCES lab(id),
    FOREIGN KEY (plant_id) REFERENCES plant(id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id)
);

-- TABLE: sample_attachment  (satrlar: 0 — BO`SH)
CREATE TABLE sample_attachment (
    id varchar NOT NULL,
    comment varchar,
    content_type varchar,
    file_name varchar NOT NULL,
    file_size integer,
    sample_id varchar NOT NULL,
    storage_key varchar NOT NULL,
    uploaded_at timestamptz NOT NULL,
    uploaded_by_user_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: sample_collection_schedule  (satrlar: 0 — BO`SH)
CREATE TABLE sample_collection_schedule (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    assigned_user_id varchar,
    comment varchar,
    frequency_type varchar NOT NULL,
    interval_count integer NOT NULL,
    is_active boolean NOT NULL,
    last_collected_at timestamptz,
    last_collected_sample_id varchar,
    next_due_at timestamptz NOT NULL,
    plant_id varchar NOT NULL,
    sample_type_id varchar,
    sampling_point_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (sample_type_id) REFERENCES sample_type(id),
    FOREIGN KEY (sampling_point_id) REFERENCES sampling_point(id)
);

-- TABLE: sample_event  (satrlar: 0 — BO`SH)
CREATE TABLE sample_event (
    id varchar NOT NULL,
    comment varchar,
    event_code varchar NOT NULL,
    from_status_id varchar,
    payload_json jsonb,  -- [JSON matn]
    performed_at timestamptz NOT NULL,
    performed_by_user_id varchar,
    sample_id varchar NOT NULL,
    to_status_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: sample_source  (satrlar: 0 — BO`SH)
CREATE TABLE sample_source (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    description varchar,
    is_active boolean NOT NULL,
    is_control_sample boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: sample_storage_location  (satrlar: 0 — BO`SH)
CREATE TABLE sample_storage_location (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    description varchar,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: sample_type  (satrlar: 0 — BO`SH)
CREATE TABLE sample_type (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    description varchar,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: sampling_point  (satrlar: 0 — BO`SH)
CREATE TABLE sampling_point (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    section_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (section_id) REFERENCES section(id)
);

-- TABLE: scale_applications  (satrlar: 137)
CREATE TABLE scale_applications (
    id bigint NOT NULL,
    "createdAt" timestamp,  -- oraliq: 2026-10-13 … 2026-11-09
    deleted boolean NOT NULL,
    "updatedAt" timestamp,  -- oraliq: 2026-10-13 … 2026-11-09
    application_date date NOT NULL,  -- oraliq: 2026-10-13 … 2026-11-09
    brand_id varchar NOT NULL,
    brand_name varchar NOT NULL,
    product_type varchar NOT NULL,  -- RUXSAT: 'COAL', 'KAOLIN', 'GORNAYA_MASSA'; BAZADA: 'COAL' 67, 'KAOLIN' 50, 'GORNAYA_MASSA' 20
    received_at timestamptz NOT NULL,  -- oraliq: 2026-10-13 … 2026-11-09
    scale_application_id bigint NOT NULL,
    section_id varchar,
    section_name varchar,
    sender_id bigint NOT NULL,
    sender_name varchar NOT NULL,
    submitted_at timestamptz NOT NULL,  -- oraliq: 2026-10-13 … 2026-11-09
    truck_calculation_act_id varchar,
    initial_section_id varchar,  -- [har doim NULL — ishlatmang]
    initial_section_name varchar,
    initial_submission_fingerprint varchar,
    master_name varchar,
    scale_details_version bigint NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (truck_calculation_act_id) REFERENCES truck_calculation_acts(id)
);

-- TABLE: scale_registry_import_checkpoint  (satrlar: 1)
CREATE TABLE scale_registry_import_checkpoint (
    sync_key varchar NOT NULL,
    last_imported_date date NOT NULL,  -- oraliq: 2026-10-12 … 2026-10-12
    PRIMARY KEY (sync_key)
);

-- TABLE: scale_shipment_company_total  (satrlar: 0 — BO`SH)
CREATE TABLE scale_shipment_company_total (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    company_key varchar NOT NULL,
    company_name varchar NOT NULL,
    report_date date NOT NULL,
    tonnage numeric(19,6) NOT NULL,
    act_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (act_id) REFERENCES truck_calculation_acts(id)
);

-- TABLE: scale_wagon_act_delivery  (satrlar: 705)
CREATE TABLE scale_wagon_act_delivery (
    act_id varchar NOT NULL,
    "attemptedHash" varchar,
    attempts integer NOT NULL,
    "deliveredAt" timestamptz,  -- oraliq: 2026-10-24 … 2026-11-09
    "deliveredHash" varchar,
    "nextAttemptAt" timestamptz,  -- [har doim NULL — ishlatmang]
    PRIMARY KEY (act_id),
    FOREIGN KEY (act_id) REFERENCES calculation_acts(id)
);

-- TABLE: section  (satrlar: 0 — BO`SH)
CREATE TABLE section (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    workshop_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (workshop_id) REFERENCES workshop(id)
);

-- TABLE: shift  (satrlar: 0 — BO`SH)
CREATE TABLE shift (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    end_time varchar,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    start_time varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: shipment  (satrlar: 0 — BO`SH)
CREATE TABLE shipment (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    batch_id varchar,
    batch_no varchar,
    customer_code varchar,
    customer_name varchar,
    external_shipment_id varchar NOT NULL,
    external_status varchar,
    last_received_at timestamptz,
    linked_at timestamptz,
    linked_by_user_id varchar,
    lot_no varchar,
    planned_ship_at timestamptz,
    plant_id varchar NOT NULL,
    product_code varchar,
    product_name varchar,
    quality_decision_id varchar,
    quality_document_id varchar,
    quantity numeric(38,2),
    sample_id varchar,
    shipment_no varchar NOT NULL,
    shipped_at timestamptz,
    source_payload_json jsonb,  -- [JSON matn]
    source_system varchar,
    status varchar NOT NULL,
    unit varchar,
    PRIMARY KEY (id)
);

-- TABLE: specification  (satrlar: 0 — BO`SH)
CREATE TABLE specification (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    description varchar,
    effective_from timestamptz,
    effective_to timestamptz,
    is_active boolean NOT NULL,
    is_current boolean NOT NULL,
    lab_id varchar,
    lifecycle_status varchar NOT NULL,
    material_id varchar,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    product_id varchar,
    sample_type_id varchar,
    version_label varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id),
    FOREIGN KEY (sample_type_id) REFERENCES sample_type(id),
    FOREIGN KEY (lab_id) REFERENCES lab(id)
);

-- TABLE: specification_item  (satrlar: 0 — BO`SH)
CREATE TABLE specification_item (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    formula_expression varchar,
    is_active boolean NOT NULL,
    is_required boolean NOT NULL,
    max_value numeric(38,2),
    method_version_id varchar,
    min_value numeric(38,2),
    rule_type varchar NOT NULL,
    sort_order integer,
    specification_id varchar NOT NULL,
    target_value numeric(38,2),
    test_definition_id varchar NOT NULL,
    text_criterion varchar,
    unit_of_measure_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: stability_study  (satrlar: 0 — BO`SH)
CREATE TABLE stability_study (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    batch_id varchar,
    comment varchar,
    completed_at timestamptz,
    created_by_user_id varchar,
    humidity_percent numeric(38,2),
    material_id varchar,
    planned_end_at timestamptz,
    plant_id varchar NOT NULL,
    product_id varchar,
    started_at timestamptz,
    status varchar NOT NULL,
    storage_condition varchar,
    study_code varchar NOT NULL,
    temperature_celsius numeric(38,2),
    title varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: stability_time_point  (satrlar: 0 — BO`SH)
CREATE TABLE stability_time_point (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    comment varchar,
    performed_at timestamptz,
    sample_id varchar,
    scheduled_at timestamptz,
    status varchar NOT NULL,
    study_id varchar NOT NULL,
    time_point_code varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (study_id) REFERENCES stability_study(id)
);

-- TABLE: status_dictionary  (satrlar: 0 — BO`SH)
-- HOLATLAR LUG'ATI: entity_type, code, label. Status kodini joriy sxemadagi qiymatlar orqali aniqlang.
CREATE TABLE status_dictionary (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    color varchar,
    description varchar,
    entity_type varchar NOT NULL,
    is_active boolean NOT NULL,
    is_initial boolean NOT NULL,
    is_terminal boolean NOT NULL,
    label varchar NOT NULL,
    plant_id varchar NOT NULL,
    sort_order integer NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: supplier  (satrlar: 0 — BO`SH)
CREATE TABLE supplier (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: test_definition  (satrlar: 0 — BO`SH)
CREATE TABLE test_definition (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    default_due_hours integer,
    default_method_version_id varchar,
    is_active boolean NOT NULL,
    is_quantitative boolean,
    lab_id varchar NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    sample_type_id varchar,
    unit_of_measure_id varchar,
    PRIMARY KEY (id)
);

-- TABLE: test_order  (satrlar: 0 — BO`SH)
CREATE TABLE test_order (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    assigned_lab_id varchar,
    assigned_user_id varchar,
    completed_at timestamptz,
    created_by_user_id varchar,
    due_at timestamptz,
    method_version_id varchar,
    plant_id varchar NOT NULL,
    priority_id varchar,
    sample_id varchar NOT NULL,
    specification_item_id varchar,
    status_id varchar NOT NULL,  -- status_dictionary.id ga bog'langan — holatni JOIN status_dictionary sd ON sd.id = status_id orqali sd.code bo'yicha filtrlang. BAZADA (sd.code): yo'q
    test_definition_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (status_id) REFERENCES status_dictionary(id),
    FOREIGN KEY (sample_id) REFERENCES sample(id)
);

-- TABLE: tnb_act  (satrlar: 0 — BO`SH)
-- TNB NAMUNA OLISH DALOLATNOMALARI: act_no, act_date, party_no, sample_id.
CREATE TABLE tnb_act (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    act_date date NOT NULL,
    act_no integer NOT NULL,
    archived_at timestamptz,
    commission_member_one varchar,
    commission_member_three varchar,
    commission_member_two varchar,
    notes text,
    packaging_count varchar,
    party_no integer NOT NULL,
    responsible_person varchar NOT NULL,
    shift_label varchar NOT NULL,
    storage_period_months integer,
    storage_place varchar,
    sample_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (sample_id) REFERENCES tnb_sample(id)
);

-- TABLE: tnb_analysis  (satrlar: 0 — BO`SH)
-- TNB TAHLILLARI: analysis_date, analyst_full_name, status, party_id, certificate_id. inputs_json va sections_json matn ko'rinishidagi JSON. Natijani nazorat nuqtasiga bog'lash uchun mavjud FK yo'li kerak.
CREATE TABLE tnb_analysis (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    analysis_date date NOT NULL,
    analysis_slot varchar,  -- RUXSAT: 'SLOT_1', 'SLOT_2', 'SLOT_3', 'SLOT_4', 'SLOT_5', 'SLOT_6'
    analysis_time time NOT NULL,
    analyst_full_name varchar NOT NULL,
    archived_at timestamptz,
    inputs_json text,  -- [JSON matn]
    sections_json text,  -- [JSON matn]
    status varchar NOT NULL,
    certificate_id varchar,
    party_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (party_id) REFERENCES tnb_party(id),
    FOREIGN KEY (certificate_id) REFERENCES tnb_certificate(id)
);

-- TABLE: tnb_certificate  (satrlar: 0 — BO`SH)
-- TNB SERTIFIKATLARI: certificate_no, type, issue_date, source_party_id, source_analysis_id. net_weight_tons matn turida.
CREATE TABLE tnb_certificate (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    certificate_no integer NOT NULL,
    certificate_source_mode varchar,  -- RUXSAT: 'ANALYSIS', 'PARTY_AVERAGE'
    container_number varchar,
    issue_date date NOT NULL,
    loaded_date date NOT NULL,
    manufacture_date date NOT NULL,
    net_weight_tons varchar NOT NULL,
    rendered_html text,  -- [MAXFIY — o'qish taqiqlangan]
    source_analysis_id varchar,
    source_party_id varchar,
    transport_number varchar,
    type varchar NOT NULL,  -- RUXSAT: 'LOCAL', 'EXPORT'
    PRIMARY KEY (id)
);

-- TABLE: tnb_defect_slip  (satrlar: 0 — BO`SH)
-- TNB YAROQSIZLIK DALOLATNOMALARI: reason, nonconformity, slipDate, partyNumber, analysis_id.
CREATE TABLE tnb_defect_slip (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    "acceptedBy" varchar,
    comment text,
    "inspectorName" varchar,
    nonconformity text,
    "partyNumber" varchar,
    reason varchar NOT NULL,  -- RUXSAT: 'CONTAMINATION', 'EXPIRED', 'INVALID_COMPOSITION', 'DAMAGED_PACKAGE', 'TRANSPORT_ISSUE', 'MARKING', 'OTHER'
    "receiverName" varchar,
    "slipDate" date,
    "transportNumber" varchar,
    "transportType" varchar,  -- RUXSAT: 'WAGON', 'TRUCK', 'CAR'
    analysis_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (analysis_id) REFERENCES tnb_analysis(id)
);

-- TABLE: tnb_party  (satrlar: 0 — BO`SH)
-- TNB PARTIYALARI: party_no, product_name, shift_date, status. Tahlil holati katta-kichik harfli analysisStatus ustunida; act_id orqali namuna olish dalolatnomasiga bog'langan.
CREATE TABLE tnb_party (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    "analysisStatus" varchar,  -- tahlil holati; SQL da katta-kichik harfni saqlab qo'shtirnoqda yozing; RUXSAT: 'PENDING', 'PASSED', 'REJECTED'
    archived_at timestamptz,
    party_no integer NOT NULL,
    product_code varchar,
    product_name varchar,
    "rejectionReason" varchar,  -- RUXSAT: 'CONTAMINATION', 'EXPIRED', 'INVALID_COMPOSITION', 'DAMAGED_PACKAGE', 'TRANSPORT_ISSUE', 'MARKING', 'OTHER'
    shift_date date,
    shift_slot varchar,  -- RUXSAT: 'SLOT_1', 'SLOT_2', 'SLOT_3', 'SLOT_4', 'SLOT_5', 'SLOT_6'
    shift_type varchar,  -- RUXSAT: 'FIRST', 'SECOND'
    source_mode varchar,
    status varchar NOT NULL,
    act_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (act_id) REFERENCES tnb_act(id)
);

-- TABLE: tnb_product  (satrlar: 0 — BO`SH)
CREATE TABLE tnb_product (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: tnb_sample  (satrlar: 0 — BO`SH)
-- TNB NAMUNALARI: serial_no, sampled_date, has_deviation, product_id, sampling_place_id, workshop_id.
CREATE TABLE tnb_sample (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    has_deviation boolean NOT NULL,
    humidity_percent numeric(8,2) NOT NULL,
    pressure_mmhg numeric(8,2) NOT NULL,
    sampled_date date NOT NULL,
    sampled_time time NOT NULL,
    sampler_full_name varchar NOT NULL,
    serial_no integer NOT NULL,
    signature_png text,  -- [MAXFIY — o'qish taqiqlangan]
    temperature_c numeric(8,2) NOT NULL,
    workshop_id varchar,
    product_id varchar,
    sampling_place_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (product_id) REFERENCES product(id),
    FOREIGN KEY (sampling_place_id) REFERENCES tnb_sampling_place(id)
);

-- TABLE: tnb_sampling_place  (satrlar: 1)
-- TNB NAMUNA OLISH JOYLARI: code, name, is_active.
CREATE TABLE tnb_sampling_place (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-08
    code varchar NOT NULL,  -- BAZADA: '02803' 1
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: truck_calculation_acts  (satrlar: 360)
-- AVTOTRANSPORT HISOB DALOLATNOMALARI: act_number, coal_brand, product_type, total_trucks, total_weight. Sana truck_received_date; bekor qilinganlik cancelled_at da.
CREATE TABLE truck_calculation_acts (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-05 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-07 … 2026-11-09
    act_number varchar,
    arbitration_sample_weight float8,
    chunk_size_actual varchar,
    chunk_size_norm varchar,  -- [har doim NULL — ishlatmang]
    coal_brand varchar,
    coal_brand_seq bigint,  -- [har doim NULL — ishlatmang]
    destination text,  -- [har doim NULL — ishlatmang]
    fine_fraction_actual float8,
    fine_fraction_norm float8,  -- [har doim NULL — ishlatmang]
    lab_sample_weight float8,
    master_otk_checked_by varchar,
    master_otk_name varchar,
    master_section_name varchar,
    mineral_impurities_actual float8,
    mineral_impurities_norm float8,  -- [har doim NULL — ishlatmang]
    mining_site varchar,
    party_number varchar,
    party_volume float8,
    radiation_checked_by varchar,
    standard_name varchar,
    status varchar,  -- BAZADA: 'YAKUNLANDI' 345, 'KUTILMOQDA' 8, 'TAYYOR' 4, 'YUBORILDI' 2, 'BEKOR_QILINDI' 1
    total_trucks integer,
    total_weight float8,
    truck_received_date date,  -- oraliq: 2026-09-05 … 2026-11-09
    uchastka_checked_by varchar,
    zbit_checked_by varchar,  -- [har doim NULL — ishlatmang]
    radiation_result_id varchar,
    al2o3_percent float8,
    fe2o3_percent float8,
    kaolin_type varchar,  -- RUXSAT: 'PRIMARY_KAOLIN', 'SECONDARY_MULTICOLORED', 'SECONDARY_GRAY'; BAZADA: 'SECONDARY_MULTICOLORED' 81, 'PRIMARY_KAOLIN' 58, 'SECONDARY_GRAY' 30
    ppp_percent float8,
    product_type varchar,  -- RUXSAT: 'COAL', 'KAOLIN', 'GORNAYA_MASSA'; BAZADA: 'KAOLIN' 169, 'COAL' 136, 'GORNAYA_MASSA' 55
    sio2_percent float8,
    w_percent float8,
    lab_checked_by varchar,
    scale_export_hash varchar,
    scale_exported_at timestamptz,  -- oraliq: 2026-10-17 … 2026-11-09
    scale_next_export_attempt_at timestamptz,  -- oraliq: 2026-11-09 … 2026-11-09
    ready_at timestamptz,  -- oraliq: 2026-10-16 … 2026-11-09
    scale_callback_attempts integer,
    scale_callback_failed_hash varchar,
    cancellation_reason varchar,
    cancelled_at timestamptz,  -- oraliq: 2026-10-31 … 2026-10-31
    cancelled_by varchar,
    cancelled_by_user_id varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (radiation_result_id) REFERENCES calculation_radiation_results(id)
);

-- TABLE: truck_info  (satrlar: 320)
-- DALOLATNOMADAGI AVTOTRANSPORT: truck_number, weight, farm_name, truck_calculation_act_id.
CREATE TABLE truck_info (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-07 … 2026-10-19
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-07 … 2026-10-19
    truck_number varchar NOT NULL,
    weight float8,
    truck_calculation_act_id varchar,
    farm_name varchar,
    PRIMARY KEY (id),
    FOREIGN KEY (truck_calculation_act_id) REFERENCES truck_calculation_acts(id)
);

-- TABLE: uchastnik  (satrlar: 6)
-- UCHASTKALAR ma'lumotnomasi: name, description.
CREATE TABLE uchastnik (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-18
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-08-31
    description varchar,
    name varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: uchastnik_user  (satrlar: 59)
CREATE TABLE uchastnik_user (
    uchastnik_id varchar NOT NULL,
    user_id varchar NOT NULL,
    FOREIGN KEY (user_id) REFERENCES core_user(id),
    FOREIGN KEY (uchastnik_id) REFERENCES uchastnik(id)
);

-- TABLE: unit_of_measure  (satrlar: 0 — BO`SH)
CREATE TABLE unit_of_measure (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    symbol varchar,
    PRIMARY KEY (id)
);

-- TABLE: user_method_qualification  (satrlar: 0 — BO`SH)
CREATE TABLE user_method_qualification (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    certificate_no varchar,
    comment varchar,
    expires_at timestamptz,
    method_id varchar NOT NULL,
    plant_id varchar NOT NULL,
    qualified_at timestamptz,
    qualified_by_user_id varchar,
    revoked_at timestamptz,
    revoked_by_user_id varchar,
    training_hours numeric(38,2),
    user_id varchar NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (plant_id) REFERENCES plant(id)
);

-- TABLE: user_role  (satrlar: 20)
CREATE TABLE user_role (
    id varchar NOT NULL,
    assigned_at timestamptz,  -- oraliq: 2026-08-08 … 2026-11-08
    expires_at timestamptz,  -- [har doim NULL — ishlatmang]
    lab_id varchar,
    plant_id varchar,
    role_id varchar,
    scope_id varchar,
    scope_type varchar,  -- BAZADA: 'GLOBAL' 18, 'LAB' 1, 'PLANT' 1
    user_id varchar,
    workshop_id varchar,  -- [har doim NULL — ishlatmang]
    PRIMARY KEY (id)
);

-- TABLE: wagon_info  (satrlar: 10716)
-- DALOLATNOMADAGI VAGONLAR: wagon_number, weight, calculation_act_id. Bekor qilinganlik is_annulled da; bekor qilinmaganlar IS NOT TRUE bilan tanlanadi.
CREATE TABLE wagon_info (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-09-10 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-09-10 … 2026-11-09
    wagon_number varchar,
    weight float8,
    calculation_act_id varchar,
    destination text,
    departure_branch text,
    departure_station text,
    destination_assigned_at timestamptz,  -- oraliq: 2026-10-10 … 2026-11-06
    is_annulled boolean NOT NULL,
    annulled_at timestamptz,  -- oraliq: 2026-11-07 … 2026-11-07
    annulled_by varchar,
    annul_reason varchar,
    annul_notes text,  -- [har doim NULL — ishlatmang]
    PRIMARY KEY (id),
    FOREIGN KEY (calculation_act_id) REFERENCES calculation_acts(id)
);

-- TABLE: wagon_registry  (satrlar: 2300)
CREATE TABLE wagon_registry (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-11-02 … 2026-11-09
    wagon_number varchar NOT NULL,
    weight float8 NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: warehouses  (satrlar: 12)
-- OMBORLAR ma'lumotnomasi: name.
CREATE TABLE warehouses (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,  -- oraliq: 2026-08-08 … 2026-09-07
    updated_at timestamptz NOT NULL,  -- oraliq: 2026-08-18 … 2026-09-07
    name varchar,
    PRIMARY KEY (id)
);

-- TABLE: workshop  (satrlar: 0 — BO`SH)
-- SEXLAR ma'lumotnomasi: code, name, is_active.
CREATE TABLE workshop (
    id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    archived_at timestamptz,
    code varchar NOT NULL,
    is_active boolean NOT NULL,
    name varchar NOT NULL,
    plant_id varchar NOT NULL,
    PRIMARY KEY (id)
);

-- TABLE: workshop_product  (satrlar: 0 — BO`SH)
CREATE TABLE workshop_product (
    product_id varchar NOT NULL,
    workshop_id varchar NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (product_id, workshop_id)
);
