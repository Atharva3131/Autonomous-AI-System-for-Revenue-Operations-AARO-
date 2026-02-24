-- ABOA Database Initialization Script
-- This script sets up the initial database schema for the ABOA system

-- Create database if it doesn't exist (PostgreSQL)
-- Note: This is handled by Docker environment variables

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS aboa;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default schema
SET search_path TO aboa, public;

-- Create enum types
CREATE TYPE deal_stage AS ENUM (
    'lead', 'qualified', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
);

CREATE TYPE activity_type AS ENUM (
    'call', 'email', 'meeting', 'demo', 'follow_up', 'proposal_sent'
);

CREATE TYPE lead_status AS ENUM (
    'new', 'contacted', 'qualified', 'unqualified', 'converted'
);

CREATE TYPE risk_type AS ENUM (
    'stalled_deal', 'missed_followup', 'sop_deviation', 'inactive_high_value'
);

CREATE TYPE action_type AS ENUM (
    'create_task', 'update_deal', 'send_alert', 'schedule_followup'
);

CREATE TYPE approval_status AS ENUM (
    'pending', 'approved', 'denied', 'timeout', 'escalated'
);

-- Create core tables
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS sales_reps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    quota DECIMAL(15,2),
    quota_attainment DECIMAL(5,2) DEFAULT 0.0,
    pipeline_value DECIMAL(15,2) DEFAULT 0.0,
    activities_this_week INTEGER DEFAULT 0,
    avg_deal_velocity DECIMAL(10,2) DEFAULT 0.0,
    conversion_rates JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    source VARCHAR(255),
    contact_info JSONB NOT NULL,
    status lead_status DEFAULT 'new',
    last_contact TIMESTAMP WITH TIME ZONE,
    follow_up_due TIMESTAMP WITH TIME ZONE,
    estimated_value DECIMAL(15,2),
    assigned_rep_id UUID REFERENCES sales_reps(id),
    contact_attempts INTEGER DEFAULT 0,
    qualification_score DECIMAL(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    lead_id UUID REFERENCES leads(id),
    stage deal_stage DEFAULT 'lead',
    value DECIMAL(15,2) NOT NULL,
    probability DECIMAL(5,2) DEFAULT 0.0,
    close_date DATE,
    last_activity TIMESTAMP WITH TIME ZONE,
    assigned_rep_id UUID REFERENCES sales_reps(id),
    days_in_current_stage INTEGER DEFAULT 0,
    next_action_due TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_activities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    deal_id UUID REFERENCES deals(id),
    activity_type activity_type NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    rep_id UUID REFERENCES sales_reps(id),
    outcome TEXT,
    next_action_scheduled BOOLEAN DEFAULT false,
    notes TEXT,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS pipeline_risks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    risk_type risk_type NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    confidence DECIMAL(5,2) NOT NULL,
    affected_deals UUID[] DEFAULT '{}',
    severity VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    recommended_actions TEXT[],
    resolved_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sales_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action_type action_type NOT NULL,
    target_system VARCHAR(255),
    parameters JSONB DEFAULT '{}',
    prerequisites TEXT[],
    expected_outcome TEXT,
    revenue_impact DECIMAL(15,2),
    executed_at TIMESTAMP WITH TIME ZONE,
    execution_status VARCHAR(50) DEFAULT 'pending',
    execution_result JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    recommendation_id UUID,
    approver_id VARCHAR(255),
    status approval_status DEFAULT 'pending',
    timeout_at TIMESTAMP WITH TIME ZONE,
    approved_at TIMESTAMP WITH TIME ZONE,
    decision_notes TEXT,
    escalation_level INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit schema tables
CREATE TABLE IF NOT EXISTS audit.activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID,
    action VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    changes JSONB,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit.decision_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    decision_id UUID NOT NULL,
    pipeline_risk_id UUID,
    recommendation JSONB,
    human_decision JSONB,
    execution_result JSONB,
    revenue_impact JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(domain);
CREATE INDEX IF NOT EXISTS idx_sales_reps_tenant ON sales_reps(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leads_tenant ON leads(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_assigned_rep ON leads(assigned_rep_id);
CREATE INDEX IF NOT EXISTS idx_deals_tenant ON deals(tenant_id);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_assigned_rep ON deals(assigned_rep_id);
CREATE INDEX IF NOT EXISTS idx_deals_close_date ON deals(close_date);
CREATE INDEX IF NOT EXISTS idx_sales_activities_tenant ON sales_activities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_activities_deal ON sales_activities(deal_id);
CREATE INDEX IF NOT EXISTS idx_sales_activities_rep ON sales_activities(rep_id);
CREATE INDEX IF NOT EXISTS idx_sales_activities_completed ON sales_activities(completed_at);
CREATE INDEX IF NOT EXISTS idx_pipeline_risks_tenant ON pipeline_risks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_risks_detected ON pipeline_risks(detected_at);
CREATE INDEX IF NOT EXISTS idx_sales_actions_tenant ON sales_actions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_sales_actions_status ON sales_actions(execution_status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_tenant ON approval_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_audit_activity_logs_tenant ON audit.activity_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_activity_logs_timestamp ON audit.activity_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_decision_logs_tenant ON audit.decision_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_decision_logs_timestamp ON audit.decision_logs(timestamp);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sales_reps_updated_at BEFORE UPDATE ON sales_reps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deals_updated_at BEFORE UPDATE ON deals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default tenant for development
INSERT INTO tenants (id, name, domain, settings) 
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Default Tenant',
    'default.aboa.local',
    '{"features": ["all"], "limits": {"max_deals": 10000, "max_reps": 100}}'
) ON CONFLICT (domain) DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA aboa TO PUBLIC;
GRANT USAGE ON SCHEMA audit TO PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA aboa TO PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA aboa TO PUBLIC;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA audit TO PUBLIC;