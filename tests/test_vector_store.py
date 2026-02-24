"""
Tests for vector database infrastructure.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from aboa.knowledge import (
    EmbeddingService, 
    ChromaVectorStore, 
    KnowledgeConfig,
    create_vector_store,
    VectorStoreException,
    EmbeddingException,
    SalesKnowledgeManager,
    SalesKnowledgeException,
    DocumentType,
    create_sales_knowledge_manager
)


class TestEmbeddingService:
    """Test the embedding service functionality."""
    
    def test_encode_single_text(self):
        """Test encoding a single text."""
        service = EmbeddingService()
        text = "This is a test document about sales processes."
        
        embedding = service.encode_text(text)
        
        assert embedding is not None
        assert len(embedding.shape) == 1
        assert embedding.shape[0] > 0
    
    def test_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        service = EmbeddingService()
        texts = [
            "Sales process documentation",
            "Customer objection handling",
            "Deal closing strategies"
        ]
        
        embeddings = service.encode_texts(texts)
        
        assert len(embeddings) == 3
        for embedding in embeddings:
            assert embedding is not None
            assert len(embedding.shape) == 1
    
    def test_encode_empty_text_raises_exception(self):
        """Test that encoding empty text raises an exception."""
        service = EmbeddingService()
        
        with pytest.raises(EmbeddingException):
            service.encode_text("")
        
        with pytest.raises(EmbeddingException):
            service.encode_text("   ")
    
    def test_get_embedding_dimension(self):
        """Test getting embedding dimension."""
        service = EmbeddingService()
        dimension = service.get_embedding_dimension()
        
        assert isinstance(dimension, int)
        assert dimension > 0


class TestChromaVectorStore:
    """Test ChromaDB vector store functionality."""
    
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
    def vector_store(self, temp_dir):
        """Create a test vector store."""
        return ChromaVectorStore(
            collection_name="test_collection",
            persist_directory=temp_dir
        )
    
    def test_add_single_document(self, vector_store):
        """Test adding a single document."""
        content = "This is a sales playbook for handling objections."
        metadata = {"type": "playbook", "category": "objections"}
        
        doc_id = vector_store.add_document(content, metadata)
        
        assert doc_id is not None
        assert isinstance(doc_id, str)
        
        # Verify document was added
        retrieved_doc = vector_store.get_document(doc_id)
        assert retrieved_doc is not None
        assert retrieved_doc.content == content
        assert retrieved_doc.metadata == metadata
    
    def test_add_multiple_documents(self, vector_store):
        """Test adding multiple documents."""
        documents = [
            ("Sales process step 1", {"step": 1, "type": "process"}),
            ("Sales process step 2", {"step": 2, "type": "process"}),
            ("Objection handling guide", {"type": "guide", "category": "objections"})
        ]
        
        doc_ids = vector_store.add_documents(documents)
        
        assert len(doc_ids) == 3
        assert all(isinstance(doc_id, str) for doc_id in doc_ids)
        
        # Verify all documents were added
        for doc_id in doc_ids:
            doc = vector_store.get_document(doc_id)
            assert doc is not None
    
    def test_search_similar_documents(self, vector_store):
        """Test searching for similar documents."""
        # Add some test documents
        documents = [
            ("How to handle price objections in sales calls", {"type": "objection_handling"}),
            ("Sales process for enterprise deals", {"type": "sales_process"}),
            ("Closing techniques for B2B sales", {"type": "closing_techniques"}),
            ("Customer objection responses", {"type": "objection_handling"})
        ]
        
        vector_store.add_documents(documents)
        
        # Search for objection-related content
        results = vector_store.search_similar("handling customer objections", limit=2)
        
        assert len(results) <= 2
        assert all(result.similarity_score >= 0 for result in results)
        assert all("objection" in result.document.content.lower() for result in results)
    
    def test_delete_document(self, vector_store):
        """Test deleting a document."""
        content = "Document to be deleted"
        metadata = {"test": True}
        
        doc_id = vector_store.add_document(content, metadata)
        
        # Verify document exists
        assert vector_store.get_document(doc_id) is not None
        
        # Delete document
        success = vector_store.delete_document(doc_id)
        assert success is True
        
        # Verify document is gone
        assert vector_store.get_document(doc_id) is None
    
    def test_update_document(self, vector_store):
        """Test updating a document."""
        original_content = "Original content"
        original_metadata = {"version": 1}
        
        doc_id = vector_store.add_document(original_content, original_metadata)
        
        # Update content
        new_content = "Updated content"
        success = vector_store.update_document(doc_id, content=new_content)
        assert success is True
        
        # Verify update
        updated_doc = vector_store.get_document(doc_id)
        assert updated_doc.content == new_content
        assert updated_doc.metadata == original_metadata
        
        # Update metadata
        new_metadata = {"version": 2, "updated": True}
        success = vector_store.update_document(doc_id, metadata=new_metadata)
        assert success is True
        
        # Verify metadata update
        updated_doc = vector_store.get_document(doc_id)
        assert updated_doc.metadata == new_metadata
    
    def test_count_documents(self, vector_store):
        """Test counting documents."""
        assert vector_store.count_documents() == 0
        
        # Add some documents
        documents = [
            ("Doc 1", {"id": 1}),
            ("Doc 2", {"id": 2}),
            ("Doc 3", {"id": 3})
        ]
        
        vector_store.add_documents(documents)
        assert vector_store.count_documents() == 3


class TestKnowledgeConfig:
    """Test knowledge configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = KnowledgeConfig()
        
        assert config.vector_db_type == "chromadb"
        assert config.vector_db_collection == "sales_knowledge"
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.default_search_limit == 10
        assert config.similarity_threshold == 0.3


class TestVectorStoreFactory:
    """Test the vector store factory function."""
    
    def test_create_chromadb_store(self):
        """Test creating a ChromaDB store."""
        config = KnowledgeConfig(vector_db_type="chromadb")
        store = create_vector_store(config)
        
        assert isinstance(store, ChromaVectorStore)
    
    def test_create_store_with_default_config(self):
        """Test creating store with default configuration."""
        store = create_vector_store()
        
        assert isinstance(store, ChromaVectorStore)
    
    def test_unsupported_vector_db_type_raises_error(self):
        """Test that unsupported vector DB type raises an error."""
        config = KnowledgeConfig(vector_db_type="unsupported")
        
        with pytest.raises(ValueError, match="Unsupported vector database type"):
            create_vector_store(config)


class TestSalesKnowledgeManager:
    """Test the Sales Knowledge Manager functionality."""
    
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
    
    def test_store_playbook(self, knowledge_manager):
        """Test storing a sales playbook."""
        title = "Enterprise Sales Playbook"
        content = "This playbook covers enterprise sales processes including discovery, demo, and closing."
        author = "Sales Manager"
        tags = ["enterprise", "b2b", "sales"]
        
        doc_id = knowledge_manager.store_playbook(
            title=title,
            content=content,
            author=author,
            tags=tags,
            version="1.0"
        )
        
        assert doc_id is not None
        assert isinstance(doc_id, str)
        
        # Verify document was stored correctly
        stored_doc = knowledge_manager.vector_store.get_document(doc_id)
        assert stored_doc is not None
        assert stored_doc.content == content
        assert stored_doc.metadata["title"] == title
        assert stored_doc.metadata["document_type"] == DocumentType.PLAYBOOK.value
        assert stored_doc.metadata["author"] == author
        assert stored_doc.metadata["tags"] == ",".join(tags)
    
    def test_store_sop(self, knowledge_manager):
        """Test storing a sales SOP."""
        title = "Lead Qualification SOP"
        content = "Standard operating procedure for qualifying inbound leads using BANT criteria."
        
        doc_id = knowledge_manager.store_sop(
            title=title,
            content=content,
            tags=["qualification", "leads", "bant"]
        )
        
        assert doc_id is not None
        stored_doc = knowledge_manager.vector_store.get_document(doc_id)
        assert stored_doc.metadata["document_type"] == DocumentType.SOP.value
    
    def test_store_objection_handling(self, knowledge_manager):
        """Test storing objection handling scripts."""
        title = "Price Objection Responses"
        content = "Common price objections and proven responses for B2B SaaS sales."
        
        doc_id = knowledge_manager.store_objection_handling(
            title=title,
            content=content,
            tags=["objections", "pricing", "responses"]
        )
        
        assert doc_id is not None
        stored_doc = knowledge_manager.vector_store.get_document(doc_id)
        assert stored_doc.metadata["document_type"] == DocumentType.OBJECTION_HANDLING.value
    
    def test_store_qualification_framework(self, knowledge_manager):
        """Test storing qualification frameworks."""
        title = "MEDDIC Qualification Framework"
        content = "Metrics, Economic Buyer, Decision Criteria, Decision Process, Identify Pain, Champion"
        
        doc_id = knowledge_manager.store_qualification_framework(
            title=title,
            content=content,
            tags=["meddic", "qualification", "framework"]
        )
        
        assert doc_id is not None
        stored_doc = knowledge_manager.vector_store.get_document(doc_id)
        assert stored_doc.metadata["document_type"] == DocumentType.QUALIFICATION_FRAMEWORK.value