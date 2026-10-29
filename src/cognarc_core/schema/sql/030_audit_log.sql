-- tier: oss
-- 只允許 INSERT 的審計表（SPEC-07 §6、T-13；S-6 的不可改部分），以及 DecisionRecord 的不可改與自動審計。
-- 兩層保護：1. 權限只給 SELECT、INSERT；2. trigger 讓 UPDATE、DELETE、TRUNCATE 一律拋錯，對 owner 與 superuser 也有效。
SET LOCAL ROLE {{owner_role}};

CREATE TABLE core.audit_log (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES core.tenant (tenant_id),
    occurred_at timestamptz NOT NULL DEFAULT now(),
    actor text NOT NULL,
    action text NOT NULL,
    subject_ref text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);
GRANT SELECT, INSERT ON core.audit_log TO {{line_role}};
ALTER TABLE core.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.audit_log FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON core.audit_log
    USING (tenant_id = core.current_tenant_id()) WITH CHECK (tenant_id = core.current_tenant_id());

CREATE FUNCTION core.forbid_audit_modification() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    RAISE EXCEPTION '%.% 只允許 INSERT（拒絕 %）', TG_TABLE_SCHEMA, TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END
$$;
CREATE TRIGGER audit_log_no_update_delete BEFORE UPDATE OR DELETE ON core.audit_log
    FOR EACH ROW EXECUTE FUNCTION core.forbid_audit_modification();
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON core.audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION core.forbid_audit_modification();

-- DecisionRecord 不得修改或刪除；每筆決策寫入時另寫一筆審計紀錄（含內容雜湊）。
CREATE TRIGGER decision_record_no_update_delete BEFORE UPDATE OR DELETE ON core.decision_record
    FOR EACH ROW EXECUTE FUNCTION core.forbid_audit_modification();
CREATE TRIGGER decision_record_no_truncate BEFORE TRUNCATE ON core.decision_record
    FOR EACH STATEMENT EXECUTE FUNCTION core.forbid_audit_modification();

CREATE FUNCTION core.audit_decision() RETURNS trigger
    LANGUAGE plpgsql
    SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    INSERT INTO core.audit_log (tenant_id, actor, action, subject_ref, payload)
    VALUES (
        NEW.tenant_id, 'db:decision_record', 'decision_recorded', 'decision:' || NEW.decision_id,
        jsonb_build_object(
            'decision', NEW.decision,
            'subject_ref', NEW.subject_ref,
            'sha256', encode(sha256(convert_to(row_to_json(NEW)::text, 'UTF8')), 'hex')
        )
    );
    RETURN NEW;
END
$$;
CREATE TRIGGER decision_record_audited AFTER INSERT ON core.decision_record
    FOR EACH ROW EXECUTE FUNCTION core.audit_decision();

RESET ROLE;
