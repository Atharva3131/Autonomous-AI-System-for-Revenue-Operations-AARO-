"""
Unit tests for sales data connector framework.

Tests the abstract connector base class, connection manager, data normalizer,
and data validator components.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from aboa.data_ingestion.connectors import (
    AuthConfig,
    ConnectionStatus,
    DataIngestionResult,
    RateLimitConfig,
    CRMDealConnector,
    SalesActivityConnector,
    RepPerformanceConnector,
    LeadManagementConnector,
    SalesDataNormalizer,
    SalesDataValidator,
)
from aboa.models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, ContactInfo
from aboa.models.enums import ActivityType, DealStage, LeadStatus
from aboa.core.exceptions import DataIngestionError, RetryableError


def test_auth_config_creation():
    """Test AuthConfig creation with different auth types."""
    # API key auth
    api_key_auth = AuthConfig(auth_type="api_key", api_key="test-key-123")
    assert api_key_auth.auth_type == "api_key"
    assert api_key_auth.api_key == "test-key-123"
    
    # OAuth auth
    oauth_auth = AuthConfig(
        auth_type="oauth",
        oauth_token="access-token",
        oauth_refresh_token="refresh-token"
    )
    assert oauth_auth.auth_type == "oauth"
    assert oauth_auth.oauth_token == "access-token"
    
    # Basic auth
    basic_auth = AuthConfig(
        auth_type="basic",
        username="user",
        password="pass"
    )
    assert basic_auth.auth_type == "basic"
    assert basic_auth.username == "user"


def test_rate_limit_config():
    """Test RateLimitConfig with custom values."""
    config = RateLimitConfig(
        requests_per_minute=120,
        requests_per_hour=5000,
        burst_limit=20,
        backoff_factor=1.5
    )
    
    assert config.requests_per_minute == 120
    assert config.requests_per_hour == 5000
    assert config.burst_limit == 20
    assert config.backoff_factor == 1.5


def test_data_ingestion_result():
    """Test DataIngestionResult creation."""
    result = DataIngestionResult(
        success=True,
        records_processed=100,
        records_failed=5,
        errors=["Connection timeout", "Invalid data format"],
        execution_time=45.2,
        source="salesforce",
        timestamp=datetime.utcnow()
    )
    
    assert result.success is True
    assert result.records_processed == 100
    assert result.records_failed == 5
    assert len(result.errors) == 2
    assert result.source == "salesforce"


def test_connection_status_enum():
    """Test ConnectionStatus enum values."""
    assert ConnectionStatus.CONNECTED == "connected"
    assert ConnectionStatus.DISCONNECTED == "disconnected"
    assert ConnectionStatus.ERROR == "error"
    assert ConnectionStatus.RATE_LIMITED == "rate_limited"


# Test CRM Deal Connector
@pytest.mark.asyncio
async def test_crm_deal_connector_mock_data():
    """Test CRM deal connector with mock data."""
    auth_config = AuthConfig(auth_type="none")
    connector = CRMDealConnector(auth_config, use_mock_data=True)
    
    # Test connection
    status = await connector.connect()
    assert status == ConnectionStatus.CONNECTED
    
    # Test data fetching
    data = await connector.fetch_data(limit=5)
    assert len(data) == 5
    
    # Validate mock data structure
    deal = data[0]
    assert "id" in deal
    assert "stage" in deal
    assert "value" in deal
    assert "probability" in deal
    assert "assigned_rep" in deal
    
    # Test disconnection
    result = await connector.disconnect()
    assert result is True


@pytest.mark.asyncio
async def test_crm_deal_connector_real_connection():
    """Test CRM deal connector with real connection (no auth)."""
    auth_config = AuthConfig(auth_type="none")
    connector = CRMDealConnector(auth_config, use_mock_data=False)
    
    status = await connector.connect()
    assert status == ConnectionStatus.CONNECTED
    
    # Real connection should return empty data (placeholder)
    data = await connector.fetch_data(limit=5)
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_crm_deal_connector_auth_failure():
    """Test CRM deal connector with authentication failure."""
    auth_config = AuthConfig(auth_type="api_key")  # No API key provided
    connector = CRMDealConnector(auth_config, use_mock_data=False)
    
    status = await connector.connect()
    assert status == ConnectionStatus.ERROR


# Test Sales Activity Connector
@pytest.mark.asyncio
async def test_sales_activity_connector_mock_data():
    """Test sales activity connector with mock data."""
    auth_config = AuthConfig(auth_type="none")
    connector = SalesActivityConnector(auth_config, use_mock_data=True)
    
    # Test connection
    status = await connector.connect()
    assert status == ConnectionStatus.CONNECTED
    
    # Test data fetching
    data = await connector.fetch_data(limit=10)
    assert len(data) == 10
    
    # Validate mock data structure
    activity = data[0]
    assert "id" in activity
    assert "activity_type" in activity
    assert "completed_at" in activity
    assert "rep_id" in activity
    
    # Ensure at least one association exists
    assert activity.get("deal_id") is not None or activity.get("lead_id") is not None


# Test Rep Performance Connector
@pytest.mark.asyncio
async def test_rep_performance_connector_mock_data():
    """Test rep performance connector with mock data."""
    auth_config = AuthConfig(auth_type="none")
    connector = RepPerformanceConnector(auth_config, use_mock_data=True)
    
    # Test connection
    status = await connector.connect()
    assert status == ConnectionStatus.CONNECTED
    
    # Test data fetching
    data = await connector.fetch_data(limit=5)
    assert len(data) == 5
    
    # Validate mock data structure
    rep = data[0]
    assert "id" in rep
    assert "name" in rep
    assert "email" in rep
    assert "quota" in rep
    assert "quota_attainment" in rep
    assert "conversion_rates" in rep


# Test Lead Management Connector
@pytest.mark.asyncio
async def test_lead_management_connector_mock_data():
    """Test lead management connector with mock data."""
    auth_config = AuthConfig(auth_type="none")
    connector = LeadManagementConnector(auth_config, use_mock_data=True)
    
    # Test connection
    status = await connector.connect()
    assert status == ConnectionStatus.CONNECTED
    
    # Test data fetching
    data = await connector.fetch_data(limit=8)
    assert len(data) == 8
    
    # Validate mock data structure
    lead = data[0]
    assert "id" in lead
    assert "source" in lead
    assert "contact_info" in lead
    assert "status" in lead
    
    # Validate contact info structure
    contact_info = lead["contact_info"]
    assert "email" in contact_info
    assert "company" in contact_info


# Test Rate Limiting
@pytest.mark.asyncio
async def test_connector_rate_limiting():
    """Test rate limiting functionality."""
    rate_config = RateLimitConfig(requests_per_minute=2, requests_per_hour=10)
    auth_config = AuthConfig(auth_type="none")
    connector = CRMDealConnector(auth_config, rate_config, use_mock_data=True)
    
    await connector.connect()
    
    # First two requests should succeed
    await connector.fetch_data(limit=1)
    await connector.fetch_data(limit=1)
    
    # Third request should hit rate limit
    with pytest.raises(RetryableError, match="Rate limit exceeded"):
        await connector.fetch_data(limit=1)


# Test Data Normalizer
def test_sales_data_normalizer_deal():
    """Test deal data normalization."""
    raw_deal = {
        "id": "deal_123",
        "lead_id": "lead_456",
        "stage": "proposal",
        "value": 50000.0,
        "probability": 75.0,
        "close_date": "2026-03-15T00:00:00Z",  # Future date
        "last_activity": "2026-02-01T10:30:00Z",
        "assigned_rep": "rep_1",
        "days_in_current_stage": 5,
        "next_action_due": "2026-02-05T09:00:00Z",
        "contact_info": {
            "email": "contact@company.com",
            "company": "Test Company",
            "first_name": "John",
            "last_name": "Doe"
        }
    }
    
    deal = SalesDataNormalizer.normalize_deal(raw_deal)
    
    assert deal.id == "deal_123"
    assert deal.stage == DealStage.PROPOSAL
    assert deal.value == Decimal("50000.0")
    assert deal.probability == 75.0
    assert deal.contact_info.email == "contact@company.com"


def test_sales_data_normalizer_lead():
    """Test lead data normalization."""
    raw_lead = {
        "id": "lead_123",
        "source": "Website",
        "contact_info": {
            "email": "lead@company.com",
            "phone": "+1-555-123-4567",
            "company": "Lead Company",
            "title": "CEO",
            "first_name": "Jane",
            "last_name": "Smith"
        },
        "status": "qualified",
        "last_contact": "2026-02-01T14:00:00Z",  # Future date
        "follow_up_due": "2026-02-05T10:00:00Z",
        "estimated_value": 25000.0,
        "assigned_rep": "rep_2",
        "contact_attempts": 3,
        "qualification_score": 85.5
    }
    
    lead = SalesDataNormalizer.normalize_lead(raw_lead)
    
    assert lead.id == "lead_123"
    assert lead.source == "Website"
    assert lead.status == LeadStatus.QUALIFIED
    assert lead.estimated_value == Decimal("25000.0")
    assert lead.contact_attempts == 3
    assert lead.qualification_score == 85.5


def test_sales_data_normalizer_activity():
    """Test activity data normalization."""
    raw_activity = {
        "id": "activity_123",
        "deal_id": "deal_456",
        "activity_type": "call",
        "completed_at": "2026-02-01T15:30:00Z",  # Future date
        "rep_id": "rep_3",
        "outcome": "Positive",
        "next_action_scheduled": True,
        "notes": "Great conversation",
        "duration_minutes": 45
    }
    
    activity = SalesDataNormalizer.normalize_activity(raw_activity)
    
    assert activity.id == "activity_123"
    assert activity.deal_id == "deal_456"
    assert activity.activity_type == ActivityType.CALL
    assert activity.outcome == "Positive"
    assert activity.next_action_scheduled is True
    assert activity.duration_minutes == 45


def test_sales_data_normalizer_rep():
    """Test rep data normalization."""
    raw_rep = {
        "id": "rep_123",
        "name": "Sales Rep",
        "email": "rep@company.com",
        "quota": 1000000.0,
        "quota_attainment": 85.5,
        "pipeline_value": 2500000.0,
        "activities_this_week": 25,
        "avg_deal_velocity": 45.5,
        "conversion_rates": {
            "prospecting_to_qualification": 25.0,
            "qualification_to_needs_analysis": 60.0
        },
        "active": True,
        "hire_date": "2023-01-15T00:00:00Z"
    }
    
    rep = SalesDataNormalizer.normalize_rep(raw_rep)
    
    assert rep.id == "rep_123"
    assert rep.name == "Sales Rep"
    assert rep.quota == Decimal("1000000.0")
    assert rep.quota_attainment == 85.5
    assert rep.conversion_rates["prospecting_to_qualification"] == 25.0


# Test Data Validator
def test_sales_data_validator_deal():
    """Test deal data validation."""
    # Valid deal
    valid_deal = Deal(
        id="deal_123",
        stage=DealStage.PROPOSAL,
        value=Decimal("50000"),
        probability=75.0,
        close_date=datetime.utcnow() + timedelta(days=30),
        assigned_rep="rep_1"
    )
    
    errors = SalesDataValidator.validate_deal(valid_deal)
    assert len(errors) == 0
    
    # Test individual validation errors by creating valid deals and checking custom validation
    # Test past close date for open deal
    past_deal = Deal(
        id="deal_456",
        stage=DealStage.PROPOSAL,
        value=Decimal("50000"),
        probability=75.0,
        close_date=datetime.utcnow() + timedelta(days=30),  # Valid for creation
        assigned_rep="rep_1",
        days_in_current_stage=10
    )
    # Manually set past date to test validator
    past_deal.close_date = datetime.utcnow() - timedelta(days=1)
    errors = SalesDataValidator.validate_deal(past_deal)
    assert "Close date cannot be in the past for open deals" in errors
    
    # Test negative days in current stage - this should be caught by Pydantic
    try:
        Deal(
            id="deal_789",
            stage=DealStage.PROPOSAL,
            value=Decimal("50000"),
            probability=75.0,
            close_date=datetime.utcnow() + timedelta(days=30),
            assigned_rep="rep_1",
            days_in_current_stage=-5
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "days_in_current_stage" in str(e)


def test_sales_data_validator_lead():
    """Test lead data validation."""
    # Valid lead
    valid_lead = Lead(
        id="lead_123",
        source="Website",
        contact_info=ContactInfo(email="test@company.com"),
        status=LeadStatus.QUALIFIED,
        contact_attempts=2,
        qualification_score=85.0,
        estimated_value=Decimal("25000")
    )
    
    errors = SalesDataValidator.validate_lead(valid_lead)
    assert len(errors) == 0
    
    # Test lead with no contact info
    no_contact_lead = Lead(
        id="lead_456",
        source="Website",
        contact_info=ContactInfo(),  # No email or phone
        status=LeadStatus.QUALIFIED,
        contact_attempts=2,
        qualification_score=85.0,
        estimated_value=Decimal("25000")
    )
    
    errors = SalesDataValidator.validate_lead(no_contact_lead)
    assert "Lead must have either email or phone contact information" in errors
    
    # Test Pydantic validation errors
    try:
        Lead(
            id="lead_789",
            source="Website",
            contact_info=ContactInfo(email="test@company.com"),
            status=LeadStatus.QUALIFIED,
            contact_attempts=-1,  # Negative attempts
            qualification_score=150.0,  # Invalid score
            estimated_value=Decimal("-1000")  # Negative value
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "contact_attempts" in str(e)
        assert "qualification_score" in str(e)
        assert "estimated_value" in str(e)


def test_sales_data_validator_activity():
    """Test activity data validation."""
    # Valid activity
    valid_activity = SalesActivity(
        id="activity_123",
        deal_id="deal_456",
        activity_type=ActivityType.CALL,
        completed_at=datetime.utcnow() - timedelta(hours=1),
        rep_id="rep_1",
        duration_minutes=30
    )
    
    errors = SalesDataValidator.validate_activity(valid_activity)
    assert len(errors) == 0
    
    # Test future completion time
    future_activity = SalesActivity(
        id="activity_789",
        deal_id="deal_456",
        activity_type=ActivityType.CALL,
        completed_at=datetime.utcnow() + timedelta(hours=1),  # Future time
        rep_id="rep_1",
        duration_minutes=30
    )
    
    errors = SalesDataValidator.validate_activity(future_activity)
    assert "Activity completion time cannot be in the future" in errors
    
    # Test Pydantic validation for missing association
    try:
        SalesActivity(
            id="activity_456",
            # No deal_id or lead_id
            activity_type=ActivityType.CALL,
            completed_at=datetime.utcnow() - timedelta(hours=1),
            rep_id="rep_1",
            duration_minutes=30
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "Activity must be associated with either a deal or lead" in str(e)
    
    # Test Pydantic validation for negative duration
    try:
        SalesActivity(
            id="activity_invalid",
            deal_id="deal_456",
            activity_type=ActivityType.CALL,
            completed_at=datetime.utcnow() - timedelta(hours=1),
            rep_id="rep_1",
            duration_minutes=-10  # Negative duration
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "duration_minutes" in str(e)


def test_sales_data_validator_rep():
    """Test rep data validation."""
    # Valid rep
    valid_rep = SalesRep(
        id="rep_123",
        name="Sales Rep",
        email="rep@company.com",
        quota=Decimal("1000000"),
        quota_attainment=85.5,
        pipeline_value=Decimal("2500000"),
        activities_this_week=25,
        avg_deal_velocity=45.5,
        conversion_rates={"stage1": 25.0, "stage2": 60.0}
    )
    
    errors = SalesDataValidator.validate_rep(valid_rep)
    assert len(errors) == 0
    
    # Test Pydantic validation for invalid conversion rates
    try:
        SalesRep(
            id="rep_456",
            name="Sales Rep",
            email="rep@company.com",
            quota=Decimal("1000000"),
            quota_attainment=85.5,
            pipeline_value=Decimal("2500000"),
            activities_this_week=25,
            avg_deal_velocity=45.5,
            conversion_rates={"stage1": 150.0}  # Invalid conversion rate
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "Conversion rate for stage1 must be between 0 and 100" in str(e)
    
    # Test Pydantic validation errors for negative values
    try:
        SalesRep(
            id="rep_invalid",
            name="Sales Rep",
            email="rep@company.com",
            quota=Decimal("-1000"),  # Negative quota
            quota_attainment=-10.0,  # Negative attainment
            pipeline_value=Decimal("-500000"),  # Negative pipeline
            activities_this_week=-5,  # Negative activities
            avg_deal_velocity=-10.0,  # Negative velocity
            conversion_rates={"stage1": 25.0}
        )
        assert False, "Should have raised validation error"
    except ValidationError as e:
        assert "quota" in str(e)
        assert "quota_attainment" in str(e)
        assert "pipeline_value" in str(e)
        assert "activities_this_week" in str(e)
        assert "avg_deal_velocity" in str(e)