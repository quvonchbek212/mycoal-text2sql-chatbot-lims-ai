-- DBA-only optional migration. This file is NOT run by the application.
-- Grants SELECT only on existing Large Objects referenced by approved business
-- JSON columns. It grants no table writes and no access to signatures/HTML.
-- Review first; run as the object owner/DBA with psql:
--   psql ... -v chatbot_role=lims-user -f grant_json_objects.sql
-- Newly created objects need equivalent grants in their creation workflow.
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
WITH referenced_objects AS (
    SELECT inputs_json AS loid FROM public.tnb_analysis WHERE inputs_json IS NOT NULL
    UNION
    SELECT sections_json FROM public.tnb_analysis WHERE sections_json IS NOT NULL
    UNION
    SELECT methodika_ids_json FROM public.tnb_incoming_control WHERE methodika_ids_json IS NOT NULL
    UNION
    SELECT methodika_snapshot_json FROM public.tnb_incoming_control WHERE methodika_snapshot_json IS NOT NULL
    UNION
    SELECT indicators_json FROM public.tnb_incoming_control WHERE indicators_json IS NOT NULL
)
SELECT format('GRANT SELECT ON LARGE OBJECT %s TO %I', objects.loid, :'chatbot_role')
FROM referenced_objects objects
JOIN pg_catalog.pg_largeobject_metadata metadata ON metadata.oid = objects.loid
ORDER BY objects.loid
\gexec
COMMIT;
