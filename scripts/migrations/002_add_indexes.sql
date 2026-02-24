-- Migration: Add Performance Indexes
-- Version: 002
-- Description: Add additional indexes for improved query performance

-- Additional indexes for better performance
CREATE INDEX IF NOT EXISTS idx_deals_value ON aboa.deals(value);
CREATE INDEX IF NOT EXISTS idx_deals_probability ON aboa.deals(probability);
CREATE INDEX IF NOT EXISTS idx_sales_activities_type ON aboa.sales_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_risks_severity ON aboa.pipeline_risks(severity);
CREATE INDEX IF NOT EXISTS idx_sales_actions_revenue_impact ON aboa.sales_actions(revenue_impact);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_deals_stage_rep ON aboa.deals(stage, assigned_rep_id);
CREATE INDEX IF NOT EXISTS idx_leads_status_rep ON aboa.leads(status, assigned_rep_id);
CREATE INDEX IF NOT EXISTS idx_sales_activities_deal_type ON aboa.sales_activities(deal_id, activity_type);

-- Partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_active_deals ON aboa.deals(stage, close_date) WHERE stage NOT IN ('closed_won', 'closed_lost');
CREATE INDEX IF NOT EXISTS idx_active_leads ON aboa.leads(status, follow_up_due) WHERE status NOT IN ('converted', 'unqualified');