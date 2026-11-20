-- Run as a DBA or an owner with grant rights in mycoallimsdb on 192.168.1.27:5432.
-- The application does not execute this file.
-- Grants schema USAGE and SELECT on existing LIMS tables/views only.
-- Future tables require a separate grant when they are created.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $grant_read_access$
DECLARE
    relation record;
BEGIN
    IF current_database() <> 'mycoallimsdb' THEN
        RAISE EXCEPTION 'Connect to mycoallimsdb before running this script';
    END IF;

    GRANT USAGE ON SCHEMA public TO "mycoallimsdb-read-user";

    FOR relation IN
        SELECT n.nspname, c.relname
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p', 'v', 'm')
          AND c.relname <> 'flyway_schema_history'
        ORDER BY c.relname
    LOOP
        EXECUTE format('GRANT SELECT ON TABLE %I.%I TO %I',
                       relation.nspname, relation.relname, 'mycoallimsdb-read-user');
    END LOOP;

    IF NOT has_schema_privilege('mycoallimsdb-read-user', 'public', 'USAGE')
       OR EXISTS (
           SELECT 1
           FROM pg_catalog.pg_class c
           JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'public'
             AND c.relkind IN ('r', 'p', 'v', 'm')
             AND c.relname <> 'flyway_schema_history'
             AND NOT has_table_privilege('mycoallimsdb-read-user', c.oid, 'SELECT')
       ) THEN
        RAISE EXCEPTION 'Incomplete grants; run as a DBA with grant rights on all target objects';
    END IF;
END;
$grant_read_access$;

COMMIT;

SELECT has_schema_privilege('mycoallimsdb-read-user', 'public', 'USAGE') AS schema_usage,
       count(*) AS readable_tables_and_views
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind IN ('r', 'p', 'v', 'm')
  AND c.relname <> 'flyway_schema_history'
  AND has_table_privilege('mycoallimsdb-read-user', c.oid, 'SELECT');
