# AARO Business Demo Script

## Demo Flow for Clients

### Opening (2 minutes)
"Let me show you how AARO works with real sales data. Imagine this is your CRM data from last week..."

### Demo Steps:

#### 1. Data Ingestion Demo
**Business Value**: "AARO connects to your existing CRM (Salesforce, HubSpot, etc.) and automatically pulls in all your sales data"

**What to show**: 
- Go to http://localhost:8000/docs
- Show "Data Ingestion" section
- Explain: "276 records already loaded - deals, leads, activities, rep performance"

#### 2. Pipeline Risk Detection
**Business Value**: "AARO analyzes your pipeline 24/7 and identifies risks before they become revenue loss"

**Demo Action**:
```
POST /decision/analyze-pipeline-risks
Body: {"deals":[],"leads":[],"activities":[],"reps":[]}
```

**Client Explanation**: 
"This would normally show risks like:
- Deals stalled for 14+ days without activity
- High-value opportunities with no scheduled next steps  
- Leads contacted fewer than 3 times
- Reps falling behind on activity targets"

#### 3. Automated Actions
**Business Value**: "When AARO detects a risk, it can automatically take action or request approval for high-impact decisions"

**Demo Action**:
```
POST /actions/execute
Body: {
  "action_type": "create_task",
  "target_system": "crm",
  "parameters": {
    "deal_id": "deal_123",
    "task_title": "Follow up on stalled $50K opportunity",
    "due_date": "2026-02-01",
    "assigned_to": "sales_rep_456"
  }
}
```

**Client Explanation**:
"AARO just created a follow-up task in your CRM for a stalled deal. No manual work required."

#### 4. Revenue Impact Tracking
**Business Value**: "Every action AARO takes is tracked for revenue impact so you can measure ROI"

**Demo Action**:
```
GET /observability/metrics
```

**Client Explanation**:
"This dashboard shows:
- $X in pipeline recovered this month
- Y hours of manual work saved
- Z% improvement in deal velocity
- ROI of the AARO system"

#### 5. Human Approval Loop
**Business Value**: "For high-impact decisions, AARO asks for human approval to ensure safety"

**Demo Action**:
```
POST /human-loop/approvals
Body: {
  "decision_type": "high_value_deal_intervention",
  "deal_value": 100000,
  "recommended_action": "Schedule urgent call with prospect",
  "reasoning": "Deal worth $100K has been stalled for 21 days"
}
```

**Client Explanation**:
"For a $100K deal at risk, AARO would send you a Slack message asking for approval before taking action."

### Closing (3 minutes)
"The result? Your sales team focuses on selling while AARO handles the operational heavy lifting."

## ROI Calculation for Clients

### Typical Results:
- **15-25% improvement** in pipeline velocity
- **10-20% reduction** in revenue leakage  
- **5-10 hours/week saved** per RevOps person
- **2-5% increase** in overall conversion rates

### Cost Justification:
"If AARO prevents just ONE $50K deal from slipping through the cracks per quarter, it pays for itself."