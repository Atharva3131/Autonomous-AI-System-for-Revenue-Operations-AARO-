"""
Sales Knowledge Manager for storing and retrieving sales SOPs, playbooks, and guidance.

This module implements the SalesKnowledgeManager class that provides semantic search
functionality for sales content, document indexing with version control, and
context retrieval for sales decision-making.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from aboa.core.exceptions import ABOAException
from aboa.knowledge.vector_store import VectorStore, Document, SearchResult
from aboa.knowledge.config import KnowledgeConfig

logger = logging.getLogger(__name__)


class SalesKnowledgeException(ABOAException):
    """Exception raised for sales knowledge management errors."""
    pass


class DocumentType(str, Enum):
    """Types of sales documents that can be stored."""
    PLAYBOOK = "playbook"
    SOP = "sop"
    OBJECTION_HANDLING = "objection_handling"
    QUALIFICATION_FRAMEWORK = "qualification_framework"
    DEAL_PATTERN = "deal_pattern"
    WINNING_STRATEGY = "winning_strategy"
    SALES_SCRIPT = "sales_script"
    METHODOLOGY = "methodology"


@dataclass
class SalesDocument:
    """Represents a sales document with metadata."""
    id: str
    title: str
    content: str
    document_type: DocumentType
    version: str
    author: Optional[str] = None
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    is_active: bool = True
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


@dataclass
class SalesContext:
    """Sales context retrieved for decision-making."""
    relevant_playbooks: List[SalesDocument]
    objection_handling: List[SalesDocument]
    successful_patterns: List[SalesDocument]
    methodologies: List[SalesDocument]
    confidence_score: float
    query: str
    retrieved_at: datetime = None
    
    def __post_init__(self):
        if self.retrieved_at is None:
            self.retrieved_at = datetime.now(timezone.utc)


class SalesKnowledgeManager:
    """
    Manager for sales knowledge storage, retrieval, and version control.
    
    This class provides functionality to:
    - Store sales playbooks, SOPs, and guidance documents
    - Perform semantic search across sales content
    - Maintain version control of sales processes
    - Retrieve contextual sales guidance for decision-making
    """
    
    def __init__(self, vector_store: VectorStore, config: Optional[KnowledgeConfig] = None):
        """
        Initialize the Sales Knowledge Manager.
        
        Args:
            vector_store: Vector database for storing and searching documents
            config: Configuration settings for knowledge management
        """
        self.vector_store = vector_store
        self.config = config or KnowledgeConfig()
        self._document_versions: Dict[str, List[str]] = {}  # doc_id -> list of version_ids
        
        logger.info("SalesKnowledgeManager initialized")
    
    def store_playbook(self, 
                      title: str, 
                      content: str, 
                      author: Optional[str] = None,
                      tags: Optional[List[str]] = None,
                      version: str = "1.0") -> str:
        """
        Store a sales playbook in the knowledge base.
        
        Args:
            title: Title of the playbook
            content: Full content of the playbook
            author: Author of the playbook
            tags: Tags for categorization
            version: Version identifier
            
        Returns:
            Document ID of the stored playbook
            
        Raises:
            SalesKnowledgeException: If storage fails
        """
        return self._store_document(
            title=title,
            content=content,
            document_type=DocumentType.PLAYBOOK,
            author=author,
            tags=tags or [],
            version=version
        )
    
    def store_sop(self, 
                  title: str, 
                  content: str, 
                  author: Optional[str] = None,
                  tags: Optional[List[str]] = None,
                  version: str = "1.0") -> str:
        """
        Store a sales SOP (Standard Operating Procedure) in the knowledge base.
        
        Args:
            title: Title of the SOP
            content: Full content of the SOP
            author: Author of the SOP
            tags: Tags for categorization
            version: Version identifier
            
        Returns:
            Document ID of the stored SOP
            
        Raises:
            SalesKnowledgeException: If storage fails
        """
        return self._store_document(
            title=title,
            content=content,
            document_type=DocumentType.SOP,
            author=author,
            tags=tags or [],
            version=version
        )
    
    def store_objection_handling(self, 
                                title: str, 
                                content: str, 
                                author: Optional[str] = None,
                                tags: Optional[List[str]] = None,
                                version: str = "1.0") -> str:
        """
        Store objection handling scripts in the knowledge base.
        
        Args:
            title: Title of the objection handling guide
            content: Full content including objections and responses
            author: Author of the guide
            tags: Tags for categorization
            version: Version identifier
            
        Returns:
            Document ID of the stored guide
            
        Raises:
            SalesKnowledgeException: If storage fails
        """
        return self._store_document(
            title=title,
            content=content,
            document_type=DocumentType.OBJECTION_HANDLING,
            author=author,
            tags=tags or [],
            version=version
        )
    
    def store_qualification_framework(self, 
                                    title: str, 
                                    content: str, 
                                    author: Optional[str] = None,
                                    tags: Optional[List[str]] = None,
                                    version: str = "1.0") -> str:
        """
        Store qualification frameworks in the knowledge base.
        
        Args:
            title: Title of the qualification framework
            content: Full content of the framework
            author: Author of the framework
            tags: Tags for categorization
            version: Version identifier
            
        Returns:
            Document ID of the stored framework
            
        Raises:
            SalesKnowledgeException: If storage fails
        """
        return self._store_document(
            title=title,
            content=content,
            document_type=DocumentType.QUALIFICATION_FRAMEWORK,
            author=author,
            tags=tags or [],
            version=version
        )
    
    def store_successful_deal_pattern(self, 
                                    title: str, 
                                    content: str, 
                                    author: Optional[str] = None,
                                    tags: Optional[List[str]] = None,
                                    version: str = "1.0") -> str:
        """
        Store successful deal patterns and winning strategies.
        
        Args:
            title: Title of the deal pattern
            content: Description of the successful pattern
            author: Author who documented the pattern
            tags: Tags for categorization
            version: Version identifier
            
        Returns:
            Document ID of the stored pattern
            
        Raises:
            SalesKnowledgeException: If storage fails
        """
        return self._store_document(
            title=title,
            content=content,
            document_type=DocumentType.DEAL_PATTERN,
            author=author,
            tags=tags or [],
            version=version
        )
    
    def search_similar(self, 
                      query: str, 
                      limit: int = None,
                      document_types: Optional[List[DocumentType]] = None,
                      tags: Optional[List[str]] = None) -> List[SearchResult]:
        """
        Search for similar sales content using semantic search.
        
        Args:
            query: Search query describing the needed guidance
            limit: Maximum number of results to return
            document_types: Filter by specific document types
            tags: Filter by specific tags
            
        Returns:
            List of search results ranked by similarity
            
        Raises:
            SalesKnowledgeException: If search fails
        """
        if not query or not query.strip():
            raise SalesKnowledgeException("Search query cannot be empty")
        
        limit = limit or self.config.default_search_limit
        
        try:
            # Build metadata filter
            filter_metadata = {}
            if document_types:
                # ChromaDB requires $in operator for list filtering
                filter_metadata["document_type"] = {"$in": [dt.value for dt in document_types]}
            if tags:
                # For tag filtering, we need to use a different approach since tags are stored as comma-separated strings
                # We'll handle this in the vector store search or post-filter the results
                pass  # Will be handled by post-filtering results
            
            # Perform semantic search
            results = self.vector_store.search_similar(
                query=query.strip(),
                limit=limit * 2 if tags else limit,  # Get more results if we need to filter by tags
                filter_metadata=filter_metadata if filter_metadata else None
            )
            
            # Post-filter by tags if specified
            if tags:
                filtered_results = []
                for result in results:
                    doc_tags_str = result.document.metadata.get("tags", "")
                    doc_tags = [tag.strip() for tag in doc_tags_str.split(",") if tag.strip()] if doc_tags_str else []
                    if any(tag in doc_tags for tag in tags):
                        filtered_results.append(result)
                results = filtered_results[:limit]
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in results 
                if result.similarity_score >= self.config.similarity_threshold
            ]
            
            logger.debug(f"Found {len(filtered_results)} relevant documents for query: {query[:50]}...")
            return filtered_results
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to search sales knowledge: {str(e)}")
    
    def get_sales_context(self, 
                         decision_type: str, 
                         additional_context: Optional[str] = None) -> SalesContext:
        """
        Retrieve comprehensive sales context for decision-making.
        
        Args:
            decision_type: Type of decision being made (e.g., "stalled_deal", "objection_handling")
            additional_context: Additional context to include in search
            
        Returns:
            SalesContext with relevant guidance and confidence score
            
        Raises:
            SalesKnowledgeException: If context retrieval fails
        """
        try:
            # Build search query
            query = decision_type
            if additional_context:
                query = f"{decision_type} {additional_context}"
            
            # Search for different types of relevant content
            playbooks = self._search_by_type(query, [DocumentType.PLAYBOOK])
            objection_handling = self._search_by_type(query, [DocumentType.OBJECTION_HANDLING])
            patterns = self._search_by_type(query, [DocumentType.DEAL_PATTERN, DocumentType.WINNING_STRATEGY])
            methodologies = self._search_by_type(query, [DocumentType.METHODOLOGY, DocumentType.SOP])
            
            # Calculate overall confidence based on result quality
            all_results = playbooks + objection_handling + patterns + methodologies
            confidence_score = self._calculate_confidence(all_results)
            
            # Convert search results to sales documents
            context = SalesContext(
                relevant_playbooks=self._convert_to_sales_documents(playbooks),
                objection_handling=self._convert_to_sales_documents(objection_handling),
                successful_patterns=self._convert_to_sales_documents(patterns),
                methodologies=self._convert_to_sales_documents(methodologies),
                confidence_score=confidence_score,
                query=query
            )
            
            logger.debug(f"Retrieved sales context for '{decision_type}' with confidence {confidence_score:.2f}")
            return context
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to retrieve sales context: {str(e)}")
    
    def update_document(self, 
                       doc_id: str, 
                       title: Optional[str] = None,
                       content: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       version: Optional[str] = None) -> str:
        """
        Update an existing document with version control.
        
        Args:
            doc_id: ID of the document to update
            title: New title (optional)
            content: New content (optional)
            tags: New tags (optional)
            version: New version identifier (optional)
            
        Returns:
            New document ID for the updated version
            
        Raises:
            SalesKnowledgeException: If update fails
        """
        try:
            # Get existing document
            existing_doc = self.vector_store.get_document(doc_id)
            if not existing_doc:
                raise SalesKnowledgeException(f"Document {doc_id} not found")
            
            # Create new version
            new_version = version or self._increment_version(existing_doc.metadata.get("version", "1.0"))
            new_doc_id = str(uuid.uuid4())
            
            # Prepare updated metadata
            updated_metadata = existing_doc.metadata.copy()
            updated_metadata.update({
                "version": new_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "previous_version_id": doc_id
            })
            
            if title:
                updated_metadata["title"] = title
            if tags is not None:
                updated_metadata["tags"] = ",".join(tags)  # Convert list to comma-separated string
            
            # Store new version
            updated_content = content if content is not None else existing_doc.content
            self.vector_store.add_document(
                content=updated_content,
                metadata=updated_metadata,
                doc_id=new_doc_id
            )
            
            # Update version tracking
            base_doc_id = existing_doc.metadata.get("base_document_id", doc_id)
            if base_doc_id not in self._document_versions:
                self._document_versions[base_doc_id] = [doc_id]
            self._document_versions[base_doc_id].append(new_doc_id)
            
            # Mark old version as inactive
            old_metadata = existing_doc.metadata.copy()
            old_metadata["is_active"] = "false"
            self.vector_store.update_document(doc_id, metadata=old_metadata)
            
            logger.info(f"Updated document {doc_id} to new version {new_version} with ID {new_doc_id}")
            return new_doc_id
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to update document: {str(e)}")
    
    def get_document_versions(self, base_doc_id: str) -> List[Dict[str, Any]]:
        """
        Get all versions of a document.
        
        Args:
            base_doc_id: Base document ID
            
        Returns:
            List of document version information
            
        Raises:
            SalesKnowledgeException: If retrieval fails
        """
        try:
            if base_doc_id not in self._document_versions:
                return []
            
            versions = []
            for version_id in self._document_versions[base_doc_id]:
                doc = self.vector_store.get_document(version_id)
                if doc:
                    versions.append({
                        "id": version_id,
                        "version": doc.metadata.get("version", "unknown"),
                        "title": doc.metadata.get("title", "Untitled"),
                        "created_at": doc.metadata.get("created_at"),
                        "updated_at": doc.metadata.get("updated_at"),
                        "is_active": doc.metadata.get("is_active", "true") == "true",
                        "author": doc.metadata.get("author")
                    })
            
            # Sort by version
            versions.sort(key=lambda x: x["version"])
            return versions
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to get document versions: {str(e)}")
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from the knowledge base.
        
        Args:
            doc_id: ID of the document to delete
            
        Returns:
            True if deletion was successful
            
        Raises:
            SalesKnowledgeException: If deletion fails
        """
        try:
            success = self.vector_store.delete_document(doc_id)
            if success:
                logger.info(f"Deleted document {doc_id} from knowledge base")
            return success
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to delete document: {str(e)}")
    
    def get_document_count(self) -> int:
        """
        Get the total number of documents in the knowledge base.
        
        Returns:
            Total document count
        """
        try:
            return self.vector_store.count_documents()
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to get document count: {str(e)}")
    
    def _store_document(self, 
                       title: str, 
                       content: str, 
                       document_type: DocumentType,
                       author: Optional[str] = None,
                       tags: Optional[List[str]] = None,
                       version: str = "1.0") -> str:
        """Internal method to store a document with metadata."""
        if not title or not title.strip():
            raise SalesKnowledgeException("Document title cannot be empty")
        if not content or not content.strip():
            raise SalesKnowledgeException("Document content cannot be empty")
        
        try:
            doc_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            metadata = {
                "title": title.strip(),
                "document_type": document_type.value,
                "version": version,
                "author": author or "",  # ChromaDB doesn't accept None values
                "tags": ",".join(tags or []),  # Convert list to comma-separated string for ChromaDB
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "is_active": "true",  # ChromaDB prefers string values
                "base_document_id": doc_id
            }
            
            # Store in vector database
            stored_id = self.vector_store.add_document(
                content=content.strip(),
                metadata=metadata,
                doc_id=doc_id
            )
            
            # Initialize version tracking
            self._document_versions[doc_id] = [stored_id]
            
            logger.info(f"Stored {document_type.value} '{title}' with ID {stored_id}")
            return stored_id
            
        except Exception as e:
            raise SalesKnowledgeException(f"Failed to store document: {str(e)}")
    
    def _search_by_type(self, query: str, document_types: List[DocumentType], limit: int = 5) -> List[SearchResult]:
        """Search for documents of specific types."""
        try:
            return self.search_similar(
                query=query,
                limit=limit,
                document_types=document_types
            )
        except Exception:
            return []
    
    def _convert_to_sales_documents(self, search_results: List[SearchResult]) -> List[SalesDocument]:
        """Convert search results to SalesDocument objects."""
        documents = []
        for result in search_results:
            try:
                doc = result.document
                # Convert comma-separated tags back to list
                tags_str = doc.metadata.get("tags", "")
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []
                
                sales_doc = SalesDocument(
                    id=doc.id,
                    title=doc.metadata.get("title", "Untitled"),
                    content=doc.content,
                    document_type=DocumentType(doc.metadata.get("document_type", "playbook")),
                    version=doc.metadata.get("version", "1.0"),
                    author=doc.metadata.get("author"),
                    tags=tags,
                    created_at=datetime.fromisoformat(doc.metadata["created_at"]) if doc.metadata.get("created_at") else None,
                    updated_at=datetime.fromisoformat(doc.metadata["updated_at"]) if doc.metadata.get("updated_at") else None,
                    is_active=doc.metadata.get("is_active", "true") == "true"
                )
                documents.append(sales_doc)
            except Exception as e:
                logger.warning(f"Failed to convert search result to SalesDocument: {str(e)}")
                continue
        
        return documents
    
    def _calculate_confidence(self, search_results: List[SearchResult]) -> float:
        """Calculate confidence score based on search result quality."""
        if not search_results:
            return 0.0
        
        # Calculate average similarity score
        avg_similarity = sum(result.similarity_score for result in search_results) / len(search_results)
        
        # Boost confidence if we have multiple relevant results
        result_count_boost = min(len(search_results) / 10.0, 0.2)  # Max 20% boost
        
        # Final confidence is average similarity plus result count boost
        confidence = min((avg_similarity + result_count_boost) * 100, 100.0)
        
        return round(confidence, 2)
    
    def _increment_version(self, current_version: str) -> str:
        """Increment version number."""
        try:
            parts = current_version.split(".")
            if len(parts) >= 2:
                major, minor = int(parts[0]), int(parts[1])
                return f"{major}.{minor + 1}"
            else:
                return "1.1"
        except (ValueError, IndexError):
            return "1.1"