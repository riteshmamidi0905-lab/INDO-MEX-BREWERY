-- 0002: the audit log is append-only. UPDATE and DELETE are refused by a trigger (a superuser can still drop the trigger: see P5-THREAT-MODEL.md).
CREATE FUNCTION audit_log_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only' USING ERRCODE = '42501';
END;
$$;
CREATE TRIGGER audit_log_no_update_delete BEFORE UPDATE OR DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
