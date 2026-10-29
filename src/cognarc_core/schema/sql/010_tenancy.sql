-- tier: oss
-- 租戶與租戶角色對照；RLS 以 current_user 找出租戶（SPEC-01 §2.2；I-16）。
SET LOCAL ROLE {{owner_role}};

CREATE TABLE core.tenant (
    tenant_id uuid PRIMARY KEY,
    slug text NOT NULL UNIQUE CHECK (slug ~ '^[a-z][a-z0-9]{0,30}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.tenant_role (
    role_name name PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES core.tenant (tenant_id),
    line text NOT NULL CHECK (line ~ '^[a-z][a-z0-9_]{0,30}$'),
    created_at timestamptz NOT NULL DEFAULT now()
);
-- 每個角色只看得到自己的對照列，看不到其他租戶的名稱與代碼。
ALTER TABLE core.tenant_role ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.tenant_role FORCE ROW LEVEL SECURITY;
CREATE POLICY own_mapping ON core.tenant_role FOR SELECT USING (role_name = current_user);
GRANT SELECT ON core.tenant_role TO {{line_role}};

CREATE FUNCTION core.current_tenant_id() RETURNS uuid
    LANGUAGE sql STABLE SECURITY INVOKER
    SET search_path = pg_catalog, pg_temp
AS $$
    SELECT tr.tenant_id FROM core.tenant_role AS tr
    WHERE tr.role_name = current_user AND tr.line = '{{line}}'
$$;
REVOKE ALL ON FUNCTION core.current_tenant_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION core.current_tenant_id() TO {{line_role}};

RESET ROLE;
