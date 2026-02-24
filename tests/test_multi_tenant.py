"""
Tests for multi-tenant functionality.
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from aboa.main import create_app
from aboa.core.tenant import TenantManager, TenantConfiguration, TenantPlan, TenantStatus
from aboa.core.auth import TenantAwareAuth


class TestMultiTenantSupport:
    """Test multi-tenant support functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.app = create_app()
        self.client = TestClient(self.app)
        self.tenant_manager = TenantManager()
        self.auth_handler = TenantAwareAuth(self.tenant_manager)
    
    def test_tenant_creation(self):
        """Test creating a new tenant."""
        tenant_config = self.tenant_manager.create_tenant(
            tenant_id="test_tenant",
            name="Test Tenant",
            plan=TenantPlan.PROFESSIONAL
        )
        
        assert tenant_config.tenant_id == "test_tenant"
        assert tenant_config.name == "Test Tenant"
        assert tenant_config.plan == TenantPlan.PROFESSIONAL
        assert tenant_config.status == TenantStatus.ACTIVE
        assert tenant_config.database_schema == "tenant_test_tenant"
        assert tenant_config.vector_db_collection == "tenant_test_tenant_knowledge"
    
    def test_tenant_retrieval(self):
        """Test retrieving tenant configuration."""
        # Create tenant
        self.tenant_manager.create_tenant(
            tenant_id="retrieve_test",
            name="Retrieve Test Tenant"
        )
        
        # Retrieve tenant
        tenant = self.tenant_manager.get_tenant("retrieve_test")
        assert tenant is not None
        assert tenant.tenant_id == "retrieve_test"
        assert tenant.name == "Retrieve Test Tenant"
        
        # Test non-existent tenant
        non_existent = self.tenant_manager.get_tenant("non_existent")
        assert non_existent is None
    
    def test_tenant_suspension_and_activation(self):
        """Test suspending and activating tenants."""
        # Create tenant
        tenant_config = self.tenant_manager.create_tenant(
            tenant_id="suspend_test",
            name="Suspend Test Tenant"
        )
        
        # Suspend tenant
        suspended_tenant = self.tenant_manager.suspend_tenant("suspend_test")
        assert suspended_tenant.status == TenantStatus.SUSPENDED
        assert suspended_tenant.suspended_at is not None
        
        # Activate tenant
        activated_tenant = self.tenant_manager.activate_tenant("suspend_test")
        assert activated_tenant.status == TenantStatus.ACTIVE
        assert activated_tenant.activated_at is not None
        assert activated_tenant.suspended_at is None
    
    def test_resource_limits_by_plan(self):
        """Test resource limits are applied based on tenant plan."""
        # Starter plan
        starter_tenant = self.tenant_manager.create_tenant(
            tenant_id="starter_test",
            name="Starter Tenant",
            plan=TenantPlan.STARTER
        )
        
        assert starter_tenant.resource_limits.max_deals == 100
        assert starter_tenant.resource_limits.max_leads == 500
        assert starter_tenant.resource_limits.enable_advanced_analytics is False
        
        # Enterprise plan
        enterprise_tenant = self.tenant_manager.create_tenant(
            tenant_id="enterprise_test",
            name="Enterprise Tenant",
            plan=TenantPlan.ENTERPRISE
        )
        
        assert enterprise_tenant.resource_limits.max_deals == 10000
        assert enterprise_tenant.resource_limits.max_leads == 50000
        assert enterprise_tenant.resource_limits.enable_advanced_analytics is True
        assert enterprise_tenant.resource_limits.enable_priority_support is True
    
    def test_resource_limit_validation(self):
        """Test resource limit validation."""
        tenant_config = self.tenant_manager.create_tenant(
            tenant_id="limit_test",
            name="Limit Test Tenant",
            plan=TenantPlan.STARTER
        )
        
        # Test within limits
        within_limits = self.tenant_manager.check_resource_limits("limit_test", "deals", 50)
        assert within_limits is True
        
        # Test exceeding limits
        exceeding_limits = self.tenant_manager.check_resource_limits("limit_test", "deals", 150)
        assert exceeding_limits is False
        
        # Test resource with no limit
        no_limit = self.tenant_manager.check_resource_limits("limit_test", "unknown_resource", 1000)
        assert no_limit is True
    
    def test_tenant_access_validation(self):
        """Test tenant access validation."""
        # Create active tenant
        self.tenant_manager.create_tenant(
            tenant_id="access_test",
            name="Access Test Tenant"
        )
        
        # Test valid access
        valid_access = self.tenant_manager.validate_tenant_access("access_test", "user123")
        assert valid_access is True
        
        # Test non-existent tenant
        invalid_tenant = self.tenant_manager.validate_tenant_access("non_existent", "user123")
        assert invalid_tenant is False
        
        # Test suspended tenant
        self.tenant_manager.suspend_tenant("access_test")
        suspended_access = self.tenant_manager.validate_tenant_access("access_test", "user123")
        assert suspended_access is False
    
    def test_tenant_list_filtering(self):
        """Test listing tenants with status filtering."""
        # Create tenants with different statuses
        self.tenant_manager.create_tenant("active1", "Active Tenant 1")
        self.tenant_manager.create_tenant("active2", "Active Tenant 2")
        suspended_tenant = self.tenant_manager.create_tenant("suspended1", "Suspended Tenant 1")
        self.tenant_manager.suspend_tenant("suspended1")
        
        # Test listing all tenants
        all_tenants = self.tenant_manager.list_tenants()
        assert len(all_tenants) >= 3
        
        # Test filtering by active status
        active_tenants = self.tenant_manager.list_tenants(status=TenantStatus.ACTIVE)
        active_ids = [t.tenant_id for t in active_tenants]
        assert "active1" in active_ids
        assert "active2" in active_ids
        assert "suspended1" not in active_ids
        
        # Test filtering by suspended status
        suspended_tenants = self.tenant_manager.list_tenants(status=TenantStatus.SUSPENDED)
        suspended_ids = [t.tenant_id for t in suspended_tenants]
        assert "suspended1" in suspended_ids
        assert "active1" not in suspended_ids
    
    def test_tenant_database_isolation(self):
        """Test tenant database isolation configuration."""
        tenant_config = self.tenant_manager.create_tenant(
            tenant_id="isolation_test",
            name="Isolation Test Tenant"
        )
        
        # Test database schema isolation
        schema = self.tenant_manager.get_database_schema("isolation_test")
        assert schema == "tenant_isolation_test"
        
        # Test vector database collection isolation
        collection = self.tenant_manager.get_vector_collection("isolation_test")
        assert collection == "tenant_isolation_test_knowledge"
        
        # Test non-existent tenant
        no_schema = self.tenant_manager.get_database_schema("non_existent")
        assert no_schema is None
        
        no_collection = self.tenant_manager.get_vector_collection("non_existent")
        assert no_collection is None
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation for tenant context."""
        # Create tenant
        self.tenant_manager.create_tenant(
            tenant_id="jwt_test",
            name="JWT Test Tenant"
        )
        
        # Create access token
        token = self.auth_handler.create_access_token(
            tenant_id="jwt_test",
            user_id="user123",
            permissions=["read", "write"]
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and validate token
        payload = self.auth_handler.decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["tenant_id"] == "jwt_test"
        assert payload["permissions"] == ["read", "write"]
        assert payload["type"] == "access_token"
    
    def test_health_check_endpoint(self):
        """Test health check endpoint works with multi-tenant setup."""
        response = self.client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "aboa"
        assert "environment" in data
    
    def test_system_info_endpoint(self):
        """Test system info endpoint works with multi-tenant setup."""
        response = self.client.get("/info")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "Autonomous AI Agent for Revenue Operations"
        assert "features" in data
        assert "api_version" in data