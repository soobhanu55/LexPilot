-- 001_init.sql

CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    system_name TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_tier TEXT,
    classification_articles TEXT[],
    compliance_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ai_inventory_company_id_idx ON ai_inventory(company_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    session_id TEXT,
    agent_name TEXT,
    action TEXT,
    input JSONB,
    output JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_log_company_id_idx ON audit_log(company_id);

-- Trigger to auto-update updated_at on ai_inventory
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_ai_inventory_modtime ON ai_inventory;

CREATE TRIGGER update_ai_inventory_modtime
BEFORE UPDATE ON ai_inventory
FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
