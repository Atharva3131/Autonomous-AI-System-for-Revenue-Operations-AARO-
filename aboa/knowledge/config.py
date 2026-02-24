"""
Configuration settings for the knowledge management layer.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class KnowledgeConfig(BaseSettings):
    """Configuration for knowledge management components."""
    
    model_config = ConfigDict(env_prefix="KNOWLEDGE_", case_sensitive=False)
    
    # Vector database settings
    vector_db_type: str = Field(default="chromadb", description="Type of vector database to use")
    vector_db_collection: str = Field(default="sales_knowledge", description="Name of the vector database collection")
    vector_db_persist_dir: Optional[str] = Field(default="./data/chroma_db", description="Directory to persist vector database")
    
    # Embedding model settings
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model for embeddings")
    embedding_dimension: int = Field(default=384, description="Dimension of embedding vectors")
    
    # Search settings
    default_search_limit: int = Field(default=10, description="Default number of search results to return")
    similarity_threshold: float = Field(default=0.3, description="Minimum similarity score for search results")