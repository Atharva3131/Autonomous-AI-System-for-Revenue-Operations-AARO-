"""
Vector database interface and ChromaDB implementation for storing and retrieving embeddings.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid

import chromadb
from chromadb.config import Settings
import numpy as np

from aboa.core.exceptions import ABOAException
from aboa.knowledge.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class VectorStoreException(ABOAException):
    """Exception raised for vector store operations."""
    pass


@dataclass
class Document:
    """Represents a document stored in the vector database."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


@dataclass
class SearchResult:
    """Represents a search result from the vector database."""
    document: Document
    similarity_score: float
    distance: float


class VectorStore(ABC):
    """Abstract base class for vector database operations."""
    
    @abstractmethod
    def add_document(self, content: str, metadata: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Add a document to the vector store."""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Tuple[str, Dict[str, Any]]], doc_ids: Optional[List[str]] = None) -> List[str]:
        """Add multiple documents to the vector store."""
        pass
    
    @abstractmethod
    def search_similar(self, query: str, limit: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        pass
    
    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by ID."""
        pass
    
    @abstractmethod
    def update_document(self, doc_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a document's content or metadata."""
        pass
    
    @abstractmethod
    def count_documents(self) -> int:
        """Get the total number of documents in the store."""
        pass


class ChromaVectorStore(VectorStore):
    """ChromaDB implementation of the vector store."""
    
    def __init__(self, 
                 collection_name: str = "sales_knowledge",
                 persist_directory: Optional[str] = "./chroma_db",
                 embedding_service: Optional[EmbeddingService] = None):
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            embedding_service: Service for generating embeddings
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.embedding_service = embedding_service or EmbeddingService()
        
        try:
            # Initialize ChromaDB client
            if persist_directory:
                self.client = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = chromadb.Client(
                    settings=Settings(anonymized_telemetry=False)
                )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Sales knowledge and SOPs storage"}
            )
            
            logger.info(f"ChromaDB vector store initialized with collection: {collection_name}")
            
        except Exception as e:
            raise VectorStoreException(f"Failed to initialize ChromaDB: {str(e)}")
    
    def add_document(self, content: str, metadata: Dict[str, Any], doc_id: Optional[str] = None) -> str:
        """Add a single document to the vector store."""
        if not content or not content.strip():
            raise VectorStoreException("Cannot add empty content")
        
        doc_id = doc_id or str(uuid.uuid4())
        
        try:
            # Generate embedding
            embedding = self.embedding_service.encode_text(content)
            
            # Add to ChromaDB
            self.collection.add(
                documents=[content],
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.debug(f"Added document {doc_id} to vector store")
            return doc_id
            
        except Exception as e:
            raise VectorStoreException(f"Failed to add document: {str(e)}")
    
    def add_documents(self, documents: List[Tuple[str, Dict[str, Any]]], doc_ids: Optional[List[str]] = None) -> List[str]:
        """Add multiple documents to the vector store."""
        if not documents:
            return []
        
        # Generate IDs if not provided
        if doc_ids is None:
            doc_ids = [str(uuid.uuid4()) for _ in documents]
        elif len(doc_ids) != len(documents):
            raise VectorStoreException("Number of document IDs must match number of documents")
        
        try:
            contents = [doc[0] for doc in documents]
            metadatas = [doc[1] for doc in documents]
            
            # Generate embeddings for all documents
            embeddings = self.embedding_service.encode_texts(contents)
            
            # Add to ChromaDB
            self.collection.add(
                documents=contents,
                embeddings=[emb.tolist() for emb in embeddings],
                metadatas=metadatas,
                ids=doc_ids
            )
            
            logger.debug(f"Added {len(documents)} documents to vector store")
            return doc_ids
            
        except Exception as e:
            raise VectorStoreException(f"Failed to add documents: {str(e)}")
    
    def search_similar(self, query: str, limit: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Search for similar documents using semantic similarity."""
        if not query or not query.strip():
            raise VectorStoreException("Cannot search with empty query")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.encode_text(query)
            
            # Prepare where clause for filtering
            where_clause = None
            if filter_metadata:
                where_clause = filter_metadata
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=min(limit, 100),  # ChromaDB has limits
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to SearchResult objects
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc_content, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    doc_id = results['ids'][0][i]
                    
                    # Convert distance to similarity score (ChromaDB uses cosine distance)
                    similarity_score = 1.0 - distance
                    
                    document = Document(
                        id=doc_id,
                        content=doc_content,
                        metadata=metadata or {}
                    )
                    
                    search_results.append(SearchResult(
                        document=document,
                        similarity_score=similarity_score,
                        distance=distance
                    ))
            
            logger.debug(f"Found {len(search_results)} similar documents for query")
            return search_results
            
        except Exception as e:
            raise VectorStoreException(f"Failed to search documents: {str(e)}")
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve a document by its ID."""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results['documents'] and len(results['documents']) > 0:
                return Document(
                    id=doc_id,
                    content=results['documents'][0],
                    metadata=results['metadatas'][0] if results['metadatas'] and len(results['metadatas']) > 0 else {}
                )
            
            return None
            
        except Exception as e:
            raise VectorStoreException(f"Failed to get document {doc_id}: {str(e)}")
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by its ID."""
        try:
            self.collection.delete(ids=[doc_id])
            logger.debug(f"Deleted document {doc_id} from vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            return False
    
    def update_document(self, doc_id: str, content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a document's content or metadata."""
        try:
            # Get existing document
            existing_doc = self.get_document(doc_id)
            if not existing_doc:
                return False
            
            # Prepare updated content and metadata
            updated_content = content if content is not None else existing_doc.content
            updated_metadata = metadata if metadata is not None else existing_doc.metadata
            
            # Delete old document and add updated one
            self.delete_document(doc_id)
            self.add_document(updated_content, updated_metadata, doc_id)
            
            logger.debug(f"Updated document {doc_id} in vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {str(e)}")
            return False
    
    def count_documents(self) -> int:
        """Get the total number of documents in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            raise VectorStoreException(f"Failed to count documents: {str(e)}")