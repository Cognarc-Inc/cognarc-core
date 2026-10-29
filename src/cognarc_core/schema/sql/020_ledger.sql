-- tier: oss
-- 決策紀錄契約的帳本物件（SPEC-01 §4）：Policy、DecisionRecord、OutcomeObservation。
-- 共通欄位：四個時間分開（event_time、published_at、available_at、ingested_at）、有效期、版本、來源、機密等級。
-- 權限：只授 SELECT、INSERT；一律不授 UPDATE、DELETE（更正另留一筆）。
-- Authorization 的欄位在各產品線差異大（投資線有額度與交易日），本層只定義語意（docs/CONTRACT.md），不建表。
SET LOCAL ROLE {{owner_role}};

CREATE TABLE core.policy (
    policy_id uuid NOT NULL,
    version integer NOT NULL CHECK (version >= 1),
    limits jsonb NOT NULL DEFAULT '{}'::jsonb,
    approval_levels jsonb NOT NULL DEFAULT '{}'::jsonb,
    approved_by uuid,
    tenant_id uuid NOT NULL REFERENCES core.tenant (tenant_id),
    workspace_id uuid NOT NULL,
    event_time timestamptz,
    published_at timestamptz,
    available_at timestamptz,
    ingested_at timestamptz,
    valid_from timestamptz,
    valid_to timestamptz,
    source_version text,
    lineage jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidentiality text NOT NULL DEFAULT 'restricted'
        CHECK (confidentiality IN ('public', 'internal', 'restricted')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (policy_id, version)
);

CREATE TABLE core.decision_record (
    decision_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_ref text NOT NULL,
    actor uuid NOT NULL,
    role text NOT NULL,
    policy_version text,
    inputs_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    decision text NOT NULL,
    decided_at timestamptz NOT NULL,
    tenant_id uuid NOT NULL REFERENCES core.tenant (tenant_id),
    workspace_id uuid NOT NULL,
    event_time timestamptz,
    published_at timestamptz,
    available_at timestamptz,
    ingested_at timestamptz,
    valid_from timestamptz,
    valid_to timestamptz,
    source_version text,
    lineage jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidentiality text NOT NULL DEFAULT 'restricted'
        CHECK (confidentiality IN ('public', 'internal', 'restricted')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE core.outcome_observation (
    observation_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_ref text NOT NULL,
    metric text NOT NULL,
    value numeric,
    observed_at timestamptz NOT NULL,
    verified boolean NOT NULL DEFAULT false,
    tenant_id uuid NOT NULL REFERENCES core.tenant (tenant_id),
    workspace_id uuid NOT NULL,
    event_time timestamptz,
    published_at timestamptz,
    available_at timestamptz,
    ingested_at timestamptz,
    valid_from timestamptz,
    valid_to timestamptz,
    source_version text,
    lineage jsonb NOT NULL DEFAULT '{}'::jsonb,
    confidentiality text NOT NULL DEFAULT 'restricted'
        CHECK (confidentiality IN ('public', 'internal', 'restricted')),
    created_at timestamptz NOT NULL DEFAULT now()
);

GRANT SELECT, INSERT ON core.policy, core.decision_record, core.outcome_observation TO {{line_role}};

-- 所有租戶資料表啟用並強制 RLS；讀（USING）與寫（WITH CHECK）都套用。
-- 未綁定租戶的角色得到 NULL，看不到任何列，也寫不進任何列。FORCE 讓 owner 也受約束。
ALTER TABLE core.policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.policy FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON core.policy
    USING (tenant_id = core.current_tenant_id()) WITH CHECK (tenant_id = core.current_tenant_id());
ALTER TABLE core.decision_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.decision_record FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON core.decision_record
    USING (tenant_id = core.current_tenant_id()) WITH CHECK (tenant_id = core.current_tenant_id());
ALTER TABLE core.outcome_observation ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.outcome_observation FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON core.outcome_observation
    USING (tenant_id = core.current_tenant_id()) WITH CHECK (tenant_id = core.current_tenant_id());

RESET ROLE;
