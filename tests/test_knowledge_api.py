"""
Tests for Sales Knowledge Management API endpoints.
"""

import pytest
import tempfile
import shutil
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from aboa.main import create_app
from aboa.knowledge.manager import SalesKnowledgeManager, DocumentType
from aboa.knowledge.config import KnowledgeConfig
from aboa.knowledge import create_vector_store
from aboa.knowledge.api import get_knowledge_manager


class TestKnowledgeAPI:
    """Test the Knowledge Management API endpoints."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Try to cleanup, but don't fail if ChromaDB is still holding files
        try:
            shutil.rmtree(temp_dir)
        except (PermissionError, OSError):
            # ChromaDB may still be holding file handles on Windows
            pass
    
    @pytest.fixture
    def knowledge_manager(self, temp_dir):
        """Create a test sales knowledge manager."""
        config = KnowledgeConfig(vector_db_persist_dir=temp_dir)
        vector_store = create_vector_store(config)
        return SalesKnowledgeManager(vector_store=vector_store, config=config)
    
    @pytest.fixture
    def client(self, knowledge_manager):
        """Create a test client with mocked knowledge manager."""
        app = create_app()
        
        # Mock the knowledge manager dependency to return the same instance
        def get_test_knowledge_manager():
            return knowledge_manager
        
        # Override the dependency
        app.dependency_overrides[get_knowledge_manager] = get_test_knowledge_manager
        
        yield TestClient(app)
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_upload_playbook(self, client):
        """Test uploading a sales playbook."""
        request_data = {
            "title": "Enterprise Sales Playbook",
            "content": "This playbook covers enterprise sales processes including discovery, demo, and closing.",
            "document_type": "playbook",
            "author": "Sales Manager",
            "tags": ["enterprise", "b2b", "sales"],
            "version": "1.0"
        }
        
        response = client.post("/api/v1/knowledge/documents", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == request_data["title"]
        assert data["document_type"] == "playbook"
        assert data["version"] == "1.0"
        assert data["author"] == "Sales Manager"
        assert data["tags"] == ["enterprise", "b2b", "sales"]
        assert data["is_active"] is True
        assert "id" in data
    
    def test_upload_sop(self, client):
        """Test uploading a sales SOP."""
        request_data = {
            "title": "Lead Qualification SOP",
            "content": "Standard operating procedure for qualifying leads using BANT criteria.",
            "document_type": "sop",
            "author": "RevOps Team",
            "tags": ["qualification", "leads"],
            "version": "2.1"
        }
        
        response = client.post("/api/v1/knowledge/documents", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == request_data["title"]
        assert data["document_type"] == "sop"
        assert data["version"] == "2.1"
    
    def test_get_document(self, client, knowledge_manager):
        """Test retrieving a document by ID."""
        # First store a document
        doc_id = knowledge_manager.store_playbook(
            title="Test Playbook",
            content="Test content for playbook",
            author="Test Author",
            tags=["test"],
            version="1.0"
        )
        
        response = client.get(f"/api/v1/knowledge/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["title"] == "Test Playbook"
        assert data["content"] == "Test content for playbook"
        assert data["author"] == "Test Author"
        assert data["tags"] == ["test"]
    
    def test_get_nonexistent_document(self, client):
        """Test retrieving a non-existent document."""
        response = client.get("/api/v1/knowledge/documents/nonexistent-id")
        
        assert response.status_code == 404
        # The response might have different error format, just check it's an error
        response_data = response.json()
        assert "detail" in response_data or "message" in response_data
    
    def test_search_documents(self, client, knowledge_manager):
        """Test searching for documents."""
        # Store some test documents
        knowledge_manager.store_playbook(
            title="Enterprise Sales Playbook",
            content="Enterprise sales process with discovery and closing techniques",
            tags=["enterprise", "sales"]
        )
        
        knowledge_manager.store_sop(
            title="Lead Qualification SOP",
            content="Standard procedure for qualifying enterprise leads",
            tags=["qualification", "enterprise"]
        )
        
        # Search for enterprise-related content
        search_request = {
            "query": "enterprise sales process",
            "limit": 10
        }
        
        response = client.post("/api/v1/knowledge/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert "query" in data
        assert "execution_time_ms" in data
        assert data["query"] == "enterprise sales process"
        assert len(data["results"]) > 0
        
        # Check result structure
        result = data["results"][0]
        assert "document" in result
        assert "similarity_score" in result
        assert "content_preview" in result
        assert result["similarity_score"] >= 0.0
    
    def test_search_with_filters(self, client, knowledge_manager):
        """Test searching with document type and tag filters."""
        # Store documents of different types
        knowledge_manager.store_playbook(
            title="Sales Playbook",
            content="Sales process documentation",
            tags=["sales", "process"]
        )
        
        knowledge_manager.store_sop(
            title="Qualification SOP",
            content="Lead qualification procedures",
            tags=["qualification", "leads"]
        )
        
        # Search with filters
        search_request = {
            "query": "sales process",
            "limit": 10,
            "document_types": ["playbook"],
            "tags": ["sales"]
        }
        
        response = client.post("/api/v1/knowledge/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0
        
        # All results should be playbooks
        for result in data["results"]:
            assert result["document"]["document_type"] == "playbook"
    
    def test_get_sales_context(self, client, knowledge_manager):
        """Test retrieving sales context for decision-making."""
        # Store relevant documents
        knowledge_manager.store_playbook(
            title="Deal Closing Playbook",
            content="Strategies for closing stalled deals and overcoming objections",
            tags=["closing", "deals"]
        )
        
        knowledge_manager.store_objection_handling(
            title="Price Objection Responses",
            content="How to handle price objections in enterprise deals",
            tags=["objections", "pricing"]
        )
        
        context_request = {
            "decision_type": "stalled_deal",
            "additional_context": "enterprise deal stuck in negotiation phase"
        }
        
        response = client.post("/api/v1/knowledge/context", json=context_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "relevant_playbooks" in data
        assert "objection_handling" in data
        assert "successful_patterns" in data
        assert "methodologies" in data
        assert "confidence_score" in data
        assert "query" in data
        assert "retrieved_at" in data
        
        assert isinstance(data["confidence_score"], (int, float))
        assert 0 <= data["confidence_score"] <= 100
    
    def test_update_document(self, client, knowledge_manager):
        """Test updating a document with version control."""
        # First store a document
        doc_id = knowledge_manager.store_playbook(
            title="Original Title",
            content="Original content",
            version="1.0"
        )
        
        # Update the document
        update_request = {
            "title": "Updated Title",
            "content": "Updated content with new information",
            "version": "1.1"
        }
        
        response = client.put(f"/api/v1/knowledge/documents/{doc_id}", json=update_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["version"] == "1.1"
        # Should have a new ID for the new version
        assert data["id"] != doc_id
    
    def test_delete_document(self, client, knowledge_manager):
        """Test deleting a document."""
        # First store a document
        doc_id = knowledge_manager.store_playbook(
            title="Document to Delete",
            content="This document will be deleted",
            version="1.0"
        )
        
        response = client.delete(f"/api/v1/knowledge/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["doc_id"] == doc_id
        
        # Verify document is deleted
        get_response = client.get(f"/api/v1/knowledge/documents/{doc_id}")
        assert get_response.status_code == 404
    
    def test_get_document_versions(self, client, knowledge_manager):
        """Test retrieving document version history."""
        # Store initial document
        doc_id = knowledge_manager.store_playbook(
            title="Versioned Document",
            content="Version 1.0 content",
            version="1.0"
        )
        
        # Update to create new version
        knowledge_manager.update_document(
            doc_id=doc_id,
            content="Version 1.1 content",
            version="1.1"
        )
        
        response = client.get(f"/api/v1/knowledge/documents/{doc_id}/versions")
        
        assert response.status_code == 200
        data = response.json()
        assert "base_document_id" in data
        assert "versions" in data
        assert "total_versions" in data
        assert data["base_document_id"] == doc_id
        assert data["total_versions"] >= 1
    
    def test_get_knowledge_stats(self, client, knowledge_manager):
        """Test retrieving knowledge base statistics."""
        # Store some documents
        knowledge_manager.store_playbook(
            title="Test Playbook",
            content="Test content"
        )
        
        response = client.get("/api/v1/knowledge/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "document_types" in data
        assert "timestamp" in data
        assert data["total_documents"] >= 1
    
    def test_health_check(self, client):
        """Test knowledge management health check."""
        response = client.get("/api/v1/knowledge/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sales_knowledge_management"
        assert "total_documents" in data
        assert "timestamp" in data
    
    def test_invalid_document_upload(self, client):
        """Test uploading invalid document data."""
        # Missing required fields
        invalid_request = {
            "title": "",  # Empty title
            "content": "Some content",
            "document_type": "playbook"
        }
        
        response = client.post("/api/v1/knowledge/documents", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_empty_search_query(self, client):
        """Test searching with empty query."""
        search_request = {
            "query": "",  # Empty query
            "limit": 10
        }
        
        response = client.post("/api/v1/knowledge/search", json=search_request)
        
        assert response.status_code == 422  # Validation error