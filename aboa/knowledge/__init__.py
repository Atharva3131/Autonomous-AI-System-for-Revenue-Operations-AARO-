"""
Knowledge management layer for ABOA system.
"""

from .embeddings import EmbeddingService, EmbeddingException
from .vector_store import VectorStore, ChromaVectorStore, Document, SearchResult, VectorStoreException
from .config import KnowledgeConfig
from .manager import SalesKnowledgeManager, SalesKnowledgeException, DocumentType, SalesDocument, SalesContext

__all__ = [
    "EmbeddingService",
    "EmbeddingException", 
    "VectorStore",
    "ChromaVectorStore",
    "Document",
    "SearchResult",
    "VectorStoreException",
    "KnowledgeConfig",
    "SalesKnowledgeManager",
    "SalesKnowledgeException",
    "DocumentType",
    "SalesDocument",
    "SalesContext",
    "create_vector_store",
    "create_sales_knowledge_manager"
]


def create_vector_store(config: KnowledgeConfig = None) -> VectorStore:
    """
    Factory function to create a vector store instance.
    
    Args:
        config: Knowledge configuration settings
        
    Returns:
        Configured vector store instance
    """
    if config is None:
        config = KnowledgeConfig()
    
    embedding_service = EmbeddingService(model_name=config.embedding_model)
    
    if config.vector_db_type.lower() == "chromadb":
        return ChromaVectorStore(
            collection_name=config.vector_db_collection,
            persist_directory=config.vector_db_persist_dir,
            embedding_service=embedding_service
        )
    else:
        raise ValueError(f"Unsupported vector database type: {config.vector_db_type}")


def create_sales_knowledge_manager(config: KnowledgeConfig = None) -> SalesKnowledgeManager:
    """
    Factory function to create a sales knowledge manager instance.
    
    Args:
        config: Knowledge configuration settings
        
    Returns:
        Configured sales knowledge manager instance
    """
    vector_store = create_vector_store(config)
    return SalesKnowledgeManager(vector_store=vector_store, config=config)