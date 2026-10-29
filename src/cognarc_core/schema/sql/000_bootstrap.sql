-- tier: oss
-- 角色與 schema（SPEC-01 §2.2；SPEC-07 §3）。叢集層級、可重跑。
-- {{owner_role}}：NOLOGIN，擁有 core schema 與所有物件。
-- {{line_role}}：NOLOGIN，一條產品線的權限集合；每租戶角色繼承它（由產品的開通流程建立）。
-- 行程的登入角色由產品建立（NOINHERIT；連線後 SET ROLE 成租戶角色才有權限）。
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{{owner_role}}') THEN
        CREATE ROLE {{owner_role}} NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{{line_role}}') THEN
        CREATE ROLE {{line_role}} NOLOGIN;
    END IF;
END
$$;

-- 時間一律 UTC。
DO $$
BEGIN
    EXECUTE format('ALTER DATABASE %I SET timezone TO %L', current_database(), 'UTC');
    EXECUTE format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database());
END
$$;
SET LOCAL timezone TO 'UTC';

CREATE SCHEMA IF NOT EXISTS core;
ALTER SCHEMA core OWNER TO {{owner_role}};
REVOKE ALL ON SCHEMA core FROM PUBLIC;
GRANT USAGE ON SCHEMA core TO {{line_role}};
ALTER TABLE core.schema_applied OWNER TO {{owner_role}};
