# Sales data connector framework
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime, timezone, timedelta

class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"

@dataclass
class AuthConfig:
    auth_type: str
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    oauth_token: Optional[str] = None
    oauth_refresh_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    backoff_factor: float = 2.0

@dataclass
class DataIngestionResult:
    success: bool
    records_processed: int
    records_failed: int
    errors: List[str]
    execution_time: float
    source: str
    timestamp: datetime

@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    backoff_factor: float = 2.0

@dataclass
class DataIngestionResult:
    success: bool
    records_processed: int
    records_failed: int
    errors: List[str]
    execution_time: float
    source: str
    timestamp: datetime

# Import additional dependencies
import asyncio
import time
import logging
import random
from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import uuid4

try:
    from dateutil import parser as date_parser
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False

from aboa.core.exceptions import DataIngestionError, ExternalIntegrationError, RetryableError
from aboa.models.revenue_entities import Deal, Lead, SalesActivity, SalesRep, ContactInfo
from aboa.models.enums import LeadStatus, DealStage, ActivityType
from aboa.core.config import get_settings

logger = logging.getLogger(__name__)

class SalesDataConnector(ABC):
    """Abstract base class for sales data connectors."""
    
    def __init__(self, auth_config: AuthConfig, rate_limit_config: Optional[RateLimitConfig] = None):
        """Initialize the connector with authentication and rate limiting."""
        self.auth_config = auth_config
        self.rate_limit_config = rate_limit_config or RateLimitConfig()
        self.connection_status = ConnectionStatus.DISCONNECTED
        self.last_request_time = 0.0
        self.request_count_minute = 0
        self.request_count_hour = 0
        self.minute_window_start = time.time()
        self.hour_window_start = time.time()
        
    @abstractmethod
    async def connect(self) -> ConnectionStatus:
        """Establish connection to the data source."""
        pass
        
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close connection to the data source."""
        pass
        
    @abstractmethod
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        pass
        
    @abstractmethod
    async def fetch_data(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch data from the source."""
        pass
        
    async def handle_error(self, error: Exception) -> None:
        """Handle errors with appropriate logging and retry logic."""
        logger.error(f"Connector error in {self.__class__.__name__}: {str(error)}")
        
        if isinstance(error, RetryableError):
            logger.info(f"Retryable error detected, will retry: {str(error)}")
        else:
            logger.error(f"Non-retryable error: {str(error)}")
            self.connection_status = ConnectionStatus.ERROR
            
    async def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        current_time = time.time()
        
        # Reset minute window if needed
        if current_time - self.minute_window_start >= 60:
            self.request_count_minute = 0
            self.minute_window_start = current_time
            
        # Reset hour window if needed  
        if current_time - self.hour_window_start >= 3600:
            self.request_count_hour = 0
            self.hour_window_start = current_time
            
        # Check limits
        if (self.request_count_minute >= self.rate_limit_config.requests_per_minute or
            self.request_count_hour >= self.rate_limit_config.requests_per_hour):
            self.connection_status = ConnectionStatus.RATE_LIMITED
            return False
            
        return True
        
    async def _increment_request_count(self) -> None:
        """Increment request counters."""
        self.request_count_minute += 1
        self.request_count_hour += 1
        self.last_request_time = time.time()
class CRMDealConnector(SalesDataConnector):
    """Connector for CRM deal and pipeline data with mock data capability."""
    
    def __init__(self, auth_config: AuthConfig, rate_limit_config: Optional[RateLimitConfig] = None, use_mock_data: bool = False):
        """Initialize the CRM deal connector."""
        super().__init__(auth_config, rate_limit_config)
        self.use_mock_data = use_mock_data
        self.source_name = "crm_deals"
        
    async def connect(self) -> ConnectionStatus:
        """Establish connection to CRM system or mock data source."""
        try:
            if self.use_mock_data:
                logger.info("Using mock data for CRM deal connector")
                self.connection_status = ConnectionStatus.CONNECTED
                return self.connection_status
                
            # In a real implementation, this would connect to actual CRM API
            logger.info("Connecting to CRM deal API...")
            await asyncio.sleep(0.1)  # Simulate connection time
            
            if self.auth_config.auth_type == "none":
                self.connection_status = ConnectionStatus.CONNECTED
            else:
                # Simulate authentication validation
                if self.auth_config.api_key or self.auth_config.oauth_token:
                    self.connection_status = ConnectionStatus.CONNECTED
                else:
                    self.connection_status = ConnectionStatus.ERROR
                    
            return self.connection_status
            
        except Exception as e:
            await self.handle_error(e)
            return ConnectionStatus.ERROR
            
    async def disconnect(self) -> bool:
        """Close connection to CRM system."""
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True
        
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        if self.use_mock_data:
            return True
            
        return self.connection_status == ConnectionStatus.CONNECTED
        
    async def fetch_data(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch deal and pipeline data."""
        if not await self._check_rate_limit():
            raise RetryableError("Rate limit exceeded")
            
        if not await self.validate_connection():
            raise DataIngestionError("Connection not valid")
            
        await self._increment_request_count()
        
        if self.use_mock_data:
            return await self._generate_mock_deals(since, limit)
        else:
            # In real implementation, this would call actual CRM API
            return await self._fetch_real_deals(since, limit)
    async def _generate_mock_deals(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate realistic mock deal data for B2B SaaS scenarios."""
        limit = limit or 50
        deals = []
        
        # Mock B2B SaaS deal scenarios
        companies = ["TechCorp Inc", "DataSoft LLC", "CloudVentures", "ScaleUp Systems", "InnovateTech"]
        stages = list(DealStage)
        
        for i in range(limit):
            deal_id = str(uuid4())
            stage = random.choice(stages)
            
            # Realistic B2B SaaS deal values
            base_value = random.choice([5000, 10000, 25000, 50000, 100000, 250000])
            value = Decimal(str(base_value + random.randint(-2000, 5000)))
            
            # Probability based on stage
            stage_probabilities = {
                DealStage.PROSPECTING: random.randint(10, 30),
                DealStage.QUALIFICATION: random.randint(20, 40),
                DealStage.NEEDS_ANALYSIS: random.randint(30, 60),
                DealStage.PROPOSAL: random.randint(50, 80),
                DealStage.NEGOTIATION: random.randint(70, 90),
                DealStage.CLOSED_WON: 100,
                DealStage.CLOSED_LOST: 0
            }
            
            close_date = datetime.utcnow() + timedelta(days=random.randint(1, 90))
            last_activity = datetime.utcnow() - timedelta(days=random.randint(0, 14))
            
            deal = {
                "id": deal_id,
                "lead_id": str(uuid4()),
                "stage": stage.value,
                "value": float(value),
                "probability": stage_probabilities[stage],
                "close_date": close_date.isoformat(),
                "last_activity": last_activity.isoformat(),
                "assigned_rep": f"rep_{random.randint(1, 10)}",
                "days_in_current_stage": random.randint(1, 30),
                "next_action_due": (datetime.utcnow() + timedelta(days=random.randint(1, 7))).isoformat(),
                "contact_info": {
                    "email": f"contact{i}@{random.choice(companies).lower().replace(' ', '')}.com",
                    "company": random.choice(companies),
                    "first_name": f"Contact{i}",
                    "last_name": "Person"
                },
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 180))).isoformat(),
                "updated_at": last_activity.isoformat()
            }
            
            # Filter by since date if provided
            if since is None or datetime.fromisoformat(deal["updated_at"].replace('Z', '+00:00')) >= since:
                deals.append(deal)
                
        return deals
        
    async def _fetch_real_deals(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch real deal data from CRM API (placeholder implementation)."""
        # This would contain actual CRM API calls
        logger.info("Fetching real deal data from CRM API...")
        await asyncio.sleep(0.5)  # Simulate API call
        return []
class SalesActivityConnector(SalesDataConnector):
    """Connector for sales activity data with mock data capability."""
    
    def __init__(self, auth_config: AuthConfig, rate_limit_config: Optional[RateLimitConfig] = None, use_mock_data: bool = False):
        """Initialize the sales activity connector."""
        super().__init__(auth_config, rate_limit_config)
        self.use_mock_data = use_mock_data
        self.source_name = "sales_activities"
        
    async def connect(self) -> ConnectionStatus:
        """Establish connection to sales activity data source."""
        try:
            if self.use_mock_data:
                logger.info("Using mock data for sales activity connector")
                self.connection_status = ConnectionStatus.CONNECTED
                return self.connection_status
                
            logger.info("Connecting to sales activity API...")
            await asyncio.sleep(0.1)
            
            if self.auth_config.auth_type == "none":
                self.connection_status = ConnectionStatus.CONNECTED
            else:
                if self.auth_config.api_key or self.auth_config.oauth_token:
                    self.connection_status = ConnectionStatus.CONNECTED
                else:
                    self.connection_status = ConnectionStatus.ERROR
                    
            return self.connection_status
            
        except Exception as e:
            await self.handle_error(e)
            return ConnectionStatus.ERROR
            
    async def disconnect(self) -> bool:
        """Close connection to sales activity system."""
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True
        
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        if self.use_mock_data:
            return True
            
        return self.connection_status == ConnectionStatus.CONNECTED
        
    async def fetch_data(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch sales activity data."""
        if not await self._check_rate_limit():
            raise RetryableError("Rate limit exceeded")
            
        if not await self.validate_connection():
            raise DataIngestionError("Connection not valid")
            
        await self._increment_request_count()
        
        if self.use_mock_data:
            return await self._generate_mock_activities(since, limit)
        else:
            return await self._fetch_real_activities(since, limit)
    async def _generate_mock_activities(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate realistic mock sales activity data."""
        limit = limit or 100
        activities = []
        
        activity_types = list(ActivityType)
        outcomes = ["Positive", "Neutral", "Negative", "No Answer", "Follow-up Needed"]
        
        for i in range(limit):
            activity_id = str(uuid4())
            activity_type = random.choice(activity_types)
            completed_at = datetime.utcnow() - timedelta(hours=random.randint(1, 168))  # Last week
            
            activity = {
                "id": activity_id,
                "deal_id": str(uuid4()) if random.choice([True, False]) else None,
                "lead_id": str(uuid4()) if random.choice([True, False]) else None,
                "activity_type": activity_type.value,
                "completed_at": completed_at.isoformat(),
                "rep_id": f"rep_{random.randint(1, 10)}",
                "outcome": random.choice(outcomes),
                "next_action_scheduled": random.choice([True, False]),
                "notes": f"Activity notes for {activity_type.value} #{i}",
                "duration_minutes": random.randint(15, 120) if activity_type in [ActivityType.CALL, ActivityType.MEETING, ActivityType.DEMO] else None,
                "created_at": completed_at.isoformat()
            }
            
            # Ensure at least one association (deal_id or lead_id)
            if not activity["deal_id"] and not activity["lead_id"]:
                activity["deal_id"] = str(uuid4())
                
            # Filter by since date if provided
            if since is None or datetime.fromisoformat(activity["completed_at"].replace('Z', '+00:00')) >= since:
                activities.append(activity)
                
        return activities
        
    async def _fetch_real_activities(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch real activity data from CRM API (placeholder implementation)."""
        logger.info("Fetching real activity data from CRM API...")
        await asyncio.sleep(0.5)
        return []
class RepPerformanceConnector(SalesDataConnector):
    """Connector for sales rep performance data with mock data capability."""
    
    def __init__(self, auth_config: AuthConfig, rate_limit_config: Optional[RateLimitConfig] = None, use_mock_data: bool = False):
        """Initialize the rep performance connector."""
        super().__init__(auth_config, rate_limit_config)
        self.use_mock_data = use_mock_data
        self.source_name = "rep_performance"
        
    async def connect(self) -> ConnectionStatus:
        """Establish connection to rep performance data source."""
        try:
            if self.use_mock_data:
                logger.info("Using mock data for rep performance connector")
                self.connection_status = ConnectionStatus.CONNECTED
                return self.connection_status
                
            logger.info("Connecting to rep performance API...")
            await asyncio.sleep(0.1)
            
            if self.auth_config.auth_type == "none":
                self.connection_status = ConnectionStatus.CONNECTED
            else:
                if self.auth_config.api_key or self.auth_config.oauth_token:
                    self.connection_status = ConnectionStatus.CONNECTED
                else:
                    self.connection_status = ConnectionStatus.ERROR
                    
            return self.connection_status
            
        except Exception as e:
            await self.handle_error(e)
            return ConnectionStatus.ERROR
            
    async def disconnect(self) -> bool:
        """Close connection to rep performance system."""
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True
        
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        if self.use_mock_data:
            return True
            
        return self.connection_status == ConnectionStatus.CONNECTED
        
    async def fetch_data(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch rep performance data."""
        if not await self._check_rate_limit():
            raise RetryableError("Rate limit exceeded")
            
        if not await self.validate_connection():
            raise DataIngestionError("Connection not valid")
            
        await self._increment_request_count()
        
        if self.use_mock_data:
            return await self._generate_mock_rep_performance(since, limit)
        else:
            return await self._fetch_real_rep_performance(since, limit)
    async def _generate_mock_rep_performance(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate realistic mock rep performance data."""
        limit = limit or 20
        reps = []
        
        rep_names = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Eva Brown", 
                    "Frank Miller", "Grace Lee", "Henry Taylor", "Ivy Chen", "Jack Anderson"]
        
        for i in range(min(limit, len(rep_names))):
            rep_id = f"rep_{i+1}"
            quota = Decimal(str(random.randint(500000, 2000000)))  # Annual quota
            attainment = random.uniform(0.4, 1.5)  # 40% to 150% attainment
            
            rep = {
                "id": rep_id,
                "name": rep_names[i],
                "email": f"{rep_names[i].lower().replace(' ', '.')}@company.com",
                "quota": float(quota),
                "quota_attainment": round(attainment * 100, 1),
                "pipeline_value": float(quota * Decimal(str(random.uniform(2.0, 5.0)))),
                "activities_this_week": random.randint(10, 50),
                "avg_deal_velocity": random.uniform(30, 120),  # Days
                "conversion_rates": {
                    "prospecting_to_qualification": random.uniform(15, 35),
                    "qualification_to_needs_analysis": random.uniform(40, 70),
                    "needs_analysis_to_proposal": random.uniform(60, 85),
                    "proposal_to_negotiation": random.uniform(70, 90),
                    "negotiation_to_closed_won": random.uniform(60, 85)
                },
                "active": True,
                "hire_date": (datetime.utcnow() - timedelta(days=random.randint(90, 1095))).isoformat(),
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(90, 1095))).isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            reps.append(rep)
                
        return reps
        
    async def _fetch_real_rep_performance(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch real rep performance data from CRM API (placeholder implementation)."""
        logger.info("Fetching real rep performance data from CRM API...")
        await asyncio.sleep(0.5)
        return []
class LeadManagementConnector(SalesDataConnector):
    """Connector for lead management data with mock data capability."""
    
    def __init__(self, auth_config: AuthConfig, rate_limit_config: Optional[RateLimitConfig] = None, use_mock_data: bool = False):
        """Initialize the lead management connector."""
        super().__init__(auth_config, rate_limit_config)
        self.use_mock_data = use_mock_data
        self.source_name = "lead_management"
        
    async def connect(self) -> ConnectionStatus:
        """Establish connection to lead management data source."""
        try:
            if self.use_mock_data:
                logger.info("Using mock data for lead management connector")
                self.connection_status = ConnectionStatus.CONNECTED
                return self.connection_status
                
            logger.info("Connecting to lead management API...")
            await asyncio.sleep(0.1)
            
            if self.auth_config.auth_type == "none":
                self.connection_status = ConnectionStatus.CONNECTED
            else:
                if self.auth_config.api_key or self.auth_config.oauth_token:
                    self.connection_status = ConnectionStatus.CONNECTED
                else:
                    self.connection_status = ConnectionStatus.ERROR
                    
            return self.connection_status
            
        except Exception as e:
            await self.handle_error(e)
            return ConnectionStatus.ERROR
            
    async def disconnect(self) -> bool:
        """Close connection to lead management system."""
        self.connection_status = ConnectionStatus.DISCONNECTED
        return True
        
    async def validate_connection(self) -> bool:
        """Validate the current connection."""
        if self.use_mock_data:
            return True
            
        return self.connection_status == ConnectionStatus.CONNECTED
        
    async def fetch_data(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch lead management data."""
        if not await self._check_rate_limit():
            raise RetryableError("Rate limit exceeded")
            
        if not await self.validate_connection():
            raise DataIngestionError("Connection not valid")
            
        await self._increment_request_count()
        
        if self.use_mock_data:
            return await self._generate_mock_leads(since, limit)
        else:
            return await self._fetch_real_leads(since, limit)
    async def _generate_mock_leads(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Generate realistic mock lead data for B2B SaaS scenarios."""
        limit = limit or 75
        leads = []
        
        sources = ["Website", "Referral", "LinkedIn", "Trade Show", "Cold Outreach", "Content Marketing"]
        companies = ["StartupCorp", "GrowthTech", "ScaleVentures", "InnovateNow", "TechForward", 
                    "DataDriven Inc", "CloudFirst LLC", "AgileWorks", "NextGen Systems", "FutureTech"]
        statuses = list(LeadStatus)
        
        for i in range(limit):
            lead_id = str(uuid4())
            status = random.choice(statuses)
            source = random.choice(sources)
            company = random.choice(companies)
            
            last_contact = None
            follow_up_due = None
            
            if status != LeadStatus.NEW:
                last_contact = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                if status in [LeadStatus.CONTACTED, LeadStatus.QUALIFIED]:
                    follow_up_due = datetime.utcnow() + timedelta(days=random.randint(1, 14))
            
            lead = {
                "id": lead_id,
                "source": source,
                "contact_info": {
                    "email": f"lead{i}@{company.lower().replace(' ', '')}.com",
                    "phone": f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    "company": company,
                    "title": random.choice(["CEO", "CTO", "VP Sales", "Director", "Manager"]),
                    "first_name": f"Lead{i}",
                    "last_name": "Contact"
                },
                "status": status.value,
                "last_contact": last_contact.isoformat() if last_contact else None,
                "follow_up_due": follow_up_due.isoformat() if follow_up_due else None,
                "estimated_value": float(Decimal(str(random.randint(10000, 500000)))) if random.choice([True, False]) else None,
                "assigned_rep": f"rep_{random.randint(1, 10)}" if status != LeadStatus.NEW else None,
                "contact_attempts": random.randint(0, 5) if status != LeadStatus.NEW else 0,
                "qualification_score": random.uniform(20, 95) if status in [LeadStatus.QUALIFIED, LeadStatus.CONVERTED] else None,
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 90))).isoformat(),
                "updated_at": (last_contact or datetime.utcnow()).isoformat()
            }
            
            # Filter by since date if provided
            if since is None or datetime.fromisoformat(lead["updated_at"].replace('Z', '+00:00')) >= since:
                leads.append(lead)
                
        return leads
        
    async def _fetch_real_leads(self, since: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch real lead data from CRM API (placeholder implementation)."""
        logger.info("Fetching real lead data from CRM API...")
        await asyncio.sleep(0.5)
        return []
class SalesDataNormalizer:
    """Normalizes sales data from different sources into standard formats."""
    
    @staticmethod
    def normalize_deal(raw_deal: Dict[str, Any]) -> Deal:
        """Normalize raw deal data into Deal entity."""
        try:
            # Handle date parsing
            close_date = raw_deal["close_date"]
            if isinstance(close_date, str):
                if DATEUTIL_AVAILABLE:
                    close_date = date_parser.parse(close_date)
                else:
                    close_date = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                    
            last_activity = raw_deal.get("last_activity")
            if last_activity and isinstance(last_activity, str):
                if DATEUTIL_AVAILABLE:
                    last_activity = date_parser.parse(last_activity)
                else:
                    last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    
            next_action_due = raw_deal.get("next_action_due")
            if next_action_due and isinstance(next_action_due, str):
                if DATEUTIL_AVAILABLE:
                    next_action_due = date_parser.parse(next_action_due)
                else:
                    next_action_due = datetime.fromisoformat(next_action_due.replace('Z', '+00:00'))
                    
            # Handle contact info
            contact_info = None
            if raw_deal.get("contact_info"):
                contact_info = ContactInfo(**raw_deal["contact_info"])
                
            return Deal(
                id=raw_deal["id"],
                lead_id=raw_deal.get("lead_id"),
                stage=DealStage(raw_deal["stage"]),
                value=Decimal(str(raw_deal["value"])),
                probability=float(raw_deal["probability"]),
                close_date=close_date,
                last_activity=last_activity,
                assigned_rep=raw_deal["assigned_rep"],
                days_in_current_stage=raw_deal.get("days_in_current_stage", 0),
                next_action_due=next_action_due,
                contact_info=contact_info
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize deal data: {str(e)}")
            raise DataIngestionError(f"Deal normalization failed: {str(e)}")
            
    @staticmethod
    def normalize_lead(raw_lead: Dict[str, Any]) -> Lead:
        """Normalize raw lead data into Lead entity."""
        try:
            # Handle date parsing
            last_contact = raw_lead.get("last_contact")
            if last_contact and isinstance(last_contact, str):
                if DATEUTIL_AVAILABLE:
                    last_contact = date_parser.parse(last_contact)
                else:
                    last_contact = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
                    
            follow_up_due = raw_lead.get("follow_up_due")
            if follow_up_due and isinstance(follow_up_due, str):
                if DATEUTIL_AVAILABLE:
                    follow_up_due = date_parser.parse(follow_up_due)
                else:
                    follow_up_due = datetime.fromisoformat(follow_up_due.replace('Z', '+00:00'))
                    
            # Handle contact info
            contact_info = ContactInfo(**raw_lead["contact_info"])
            
            # Handle estimated value
            estimated_value = raw_lead.get("estimated_value")
            if estimated_value is not None:
                estimated_value = Decimal(str(estimated_value))
                
            return Lead(
                id=raw_lead["id"],
                source=raw_lead["source"],
                contact_info=contact_info,
                status=LeadStatus(raw_lead["status"]),
                last_contact=last_contact,
                follow_up_due=follow_up_due,
                estimated_value=estimated_value,
                assigned_rep=raw_lead.get("assigned_rep"),
                contact_attempts=raw_lead.get("contact_attempts", 0),
                qualification_score=raw_lead.get("qualification_score")
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize lead data: {str(e)}")
            raise DataIngestionError(f"Lead normalization failed: {str(e)}")
    @staticmethod
    def normalize_activity(raw_activity: Dict[str, Any]) -> SalesActivity:
        """Normalize raw activity data into SalesActivity entity."""
        try:
            # Handle date parsing
            completed_at = raw_activity["completed_at"]
            if isinstance(completed_at, str):
                if DATEUTIL_AVAILABLE:
                    completed_at = date_parser.parse(completed_at)
                else:
                    completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                    
            return SalesActivity(
                id=raw_activity["id"],
                deal_id=raw_activity.get("deal_id"),
                lead_id=raw_activity.get("lead_id"),
                activity_type=ActivityType(raw_activity["activity_type"]),
                completed_at=completed_at,
                rep_id=raw_activity["rep_id"],
                outcome=raw_activity.get("outcome"),
                next_action_scheduled=raw_activity.get("next_action_scheduled", False),
                notes=raw_activity.get("notes"),
                duration_minutes=raw_activity.get("duration_minutes")
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize activity data: {str(e)}")
            raise DataIngestionError(f"Activity normalization failed: {str(e)}")
            
    @staticmethod
    def normalize_rep(raw_rep: Dict[str, Any]) -> SalesRep:
        """Normalize raw rep data into SalesRep entity."""
        try:
            # Handle date parsing
            hire_date = raw_rep.get("hire_date")
            if hire_date and isinstance(hire_date, str):
                if DATEUTIL_AVAILABLE:
                    hire_date = date_parser.parse(hire_date)
                else:
                    hire_date = datetime.fromisoformat(hire_date.replace('Z', '+00:00'))
                    
            return SalesRep(
                id=raw_rep["id"],
                name=raw_rep["name"],
                email=raw_rep["email"],
                quota=Decimal(str(raw_rep["quota"])),
                quota_attainment=float(raw_rep["quota_attainment"]),
                pipeline_value=Decimal(str(raw_rep["pipeline_value"])),
                activities_this_week=raw_rep.get("activities_this_week", 0),
                avg_deal_velocity=float(raw_rep.get("avg_deal_velocity", 0)),
                conversion_rates=raw_rep.get("conversion_rates", {}),
                active=raw_rep.get("active", True),
                hire_date=hire_date
            )
            
        except Exception as e:
            logger.error(f"Failed to normalize rep data: {str(e)}")
            raise DataIngestionError(f"Rep normalization failed: {str(e)}")
class SalesDataValidator:
    """Validates sales data quality and completeness."""
    
    @staticmethod
    def validate_deal(deal: Deal) -> List[str]:
        """Validate deal data and return list of validation errors."""
        errors = []
        
        if deal.value <= 0:
            errors.append("Deal value must be positive")
            
        if not (0 <= deal.probability <= 100):
            errors.append("Deal probability must be between 0 and 100")
            
        if deal.close_date.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0):
            if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]:
                errors.append("Close date cannot be in the past for open deals")
                
        if deal.days_in_current_stage < 0:
            errors.append("Days in current stage cannot be negative")
            
        return errors
        
    @staticmethod
    def validate_lead(lead: Lead) -> List[str]:
        """Validate lead data and return list of validation errors."""
        errors = []
        
        if not lead.contact_info.email and not lead.contact_info.phone:
            errors.append("Lead must have either email or phone contact information")
            
        if lead.contact_attempts < 0:
            errors.append("Contact attempts cannot be negative")
            
        if lead.qualification_score is not None and not (0 <= lead.qualification_score <= 100):
            errors.append("Qualification score must be between 0 and 100")
            
        if lead.estimated_value is not None and lead.estimated_value <= 0:
            errors.append("Estimated value must be positive")
            
        return errors
        
    @staticmethod
    def validate_activity(activity: SalesActivity) -> List[str]:
        """Validate activity data and return list of validation errors."""
        errors = []
        
        if not activity.deal_id and not activity.lead_id:
            errors.append("Activity must be associated with either a deal or lead")
            
        if activity.duration_minutes is not None and activity.duration_minutes <= 0:
            errors.append("Activity duration must be positive")
            
        if activity.completed_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            errors.append("Activity completion time cannot be in the future")
            
        return errors
        
    @staticmethod
    def validate_rep(rep: SalesRep) -> List[str]:
        """Validate rep data and return list of validation errors."""
        errors = []
        
        if rep.quota <= 0:
            errors.append("Rep quota must be positive")
            
        if rep.quota_attainment < 0:
            errors.append("Quota attainment cannot be negative")
            
        if rep.pipeline_value < 0:
            errors.append("Pipeline value cannot be negative")
            
        if rep.activities_this_week < 0:
            errors.append("Activities this week cannot be negative")
            
        if rep.avg_deal_velocity < 0:
            errors.append("Average deal velocity cannot be negative")
            
        for stage, rate in rep.conversion_rates.items():
            if not (0 <= rate <= 100):
                errors.append(f"Conversion rate for {stage} must be between 0 and 100")
                
        return errors