-- Migration: Enhanced Audit Tables
-- Version: 003
-- Description: Add enhanced audit and tracking capabilities

-- Add revenue impact tracking table
CREATE TABLE IF NOT EXISTS aboa.revenue_impact_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES aboa.tenants(id) ON DELETE CASCADE,
    action_id UUID REFERENCES aboa.sales_actions(id),
    deal_id UUID REFERENCES aboa.deals(id),
    impact_type VARCHAR(50) NOT NULL, -- 'pipeline_recovered', 'velocity_improved', 'deal_accelerated'
    baseline_value DECIMAL(15,2),
    actual_value DECIMAL(15,2),
    improvement_percent DECIMAL(5,2),
    measurement_date DATE NOT NULL,
    confidence_score DECIMAL(5,2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add system performance metrics table
CREATE TABLE IF NOT EXISTS aboa.system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES aboa.tenants(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}',
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add configuration history table
CREATE TABLE IF NOT EXISTS aboa.configuration_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES aboa.tenants(id) ON DELETE CASCADE,
    config_key VARCHAR(255) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    changed_by VARCHAR(255),
    change_reason TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for new tables
CREATE INDEX IF NOT EXISTS idx_revenue_impact_tenant ON aboa.revenue_impact_tracking(tenant_id);
CREATE INDEX IF NOT EXISTS idx_revenue_impact_date ON aboa.revenue_impact_tracking(measurement_date);
CREATE INDEX IF NOT EXISTS idx_revenue_impact_type ON aboa.revenue_impact_tracking(impact_type);

CREATE INDEX IF NOT EXISTS idx_system_metrics_tenant ON aboa.system_metrics(tenant_id);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON aboa.system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_recorded ON aboa.system_metrics(recorded_at);

CREATE INDEX IF NOT EXISTS idx_config_history_tenant ON aboa.configuration_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_config_history_key ON aboa.configuration_history(config_key);
CREATE INDEX IF NOT EXISTS idx_config_history_changed ON aboa.configuration_history(changed_at);