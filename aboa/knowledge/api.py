"""
Sales Knowledge Management API endpoints.

This module provides FastAPI endpoints for managing sales playbooks, SOPs,
and knowledge documents with semantic search and version control capabilities.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from pydantic import BaseModel, Field
import logging
import uuid

from aboa.core.exceptions import ABOAException
from aboa.knowledge.manager import (
    SalesKnowledgeManager, 
    SalesKnowledgeException, 
    DocumentType, 
    SalesDocument, 
    SalesContext
)
from aboa.knowledge import create_sales_knowledge_manager
from aboa.core.logging import log_business_event

logger = logging.getLogger(__name__)

# Global service instance (will be properly managed in production)
_knowledge_manager: Optional[SalesKnowledgeManager] = None

def get_knowledge_manager() -> SalesKnowledgeManager:
    """Get or create the knowledge manager instance."""
    global _knowledge_manager
    if _knowledge_manager is None:
        _knowledge_manager = create_sales_knowledge_manager()
    return _knowledge_manager

# Request/Response models
class DocumentUploadRequest(BaseModel):
    """Request model for document upload."""
    title: str = Field(..., description="Title of the document", min_length=1, max_length=200)
    content: str = Field(..., description="Content of the document", min_length=1)
    document_type: DocumentType = Field(..., description="Type of the document")
    author: Optional[str] = Field(None, description="Author of the document", max_length=100)
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    version: str = Field("1.0", description="Version identifier", max_length=20)

class DocumentUpdateRequest(BaseModel):
    """Request model for document updates."""
    title: Optional[str] = Field(None, description="New title", min_length=1, max_length=200)
    content: Optional[str] = Field(None, description="New content", min_length=1)
    tags: Optional[List[str]] = Field(None, description="New tags")
    version: Optional[str] = Field(None, description="New version identifier", max_length=20)

class DocumentResponse(BaseModel):
    """Response model for document operations."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    document_type: DocumentType = Field(..., description="Document type")
    version: str = Field(..., description="Document version")
    author: Optional[str] = Field(None, description="Document author")
    tags: List[str] = Field(..., description="Document tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Whether document is active")

class DocumentWithContentResponse(DocumentResponse):
    """Response model for document with full content."""
    content: str = Field(..., description="Document content")

class SearchRequest(BaseModel):
    """Request model for document search."""
    query: str = Field(..., description="Search query", min_length=1, max_length=500)
    limit: Optional[int] = Field(10, description="Maximum results to return", ge=1, le=100)
    document_types: Optional[List[DocumentType]] = Field(None, description="Filter by document types")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")

class SearchResultResponse(BaseModel):
    """Response model for search results."""
    document: DocumentResponse = Field(..., description="Document information")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    content_preview: str = Field(..., description="Content preview")

class SearchResponse(BaseModel):
    """Response model for search operations."""
    results: List[SearchResultResponse] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    query: str = Field(..., description="Original search query")
    execution_time_ms: float = Field(..., description="Search execution time in milliseconds")

class SalesContextRequest(BaseModel):
    """Request model for sales context retrieval."""
    decision_type: str = Field(..., description="Type of decision being made", min_length=1, max_length=100)
    additional_context: Optional[str] = Field(None, description="Additional context", max_length=1000)

class SalesContextResponse(BaseModel):
    """Response model for sales context."""
    relevant_playbooks: List[DocumentResponse] = Field(..., description="Relevant playbooks")
    objection_handling: List[DocumentResponse] = Field(..., description="Objection handling guides")
    successful_patterns: List[DocumentResponse] = Field(..., description="Successful deal patterns")
    methodologies: List[DocumentResponse] = Field(..., description="Sales methodologies")
    confidence_score: float = Field(..., description="Confidence score (0-100)")
    query: str = Field(..., description="Query used for context retrieval")
    retrieved_at: datetime = Field(..., description="Retrieval timestamp")

class DocumentVersionResponse(BaseModel):
    """Response model for document version information."""
    id: str = Field(..., description="Version ID")
    version: str = Field(..., description="Version identifier")
    title: str = Field(..., description="Document title")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Update timestamp")
    is_active: bool = Field(..., description="Whether version is active")
    author: Optional[str] = Field(None, description="Version author")

class DocumentVersionsResponse(BaseModel):
    """Response model for document versions list."""
    base_document_id: str = Field(..., description="Base document ID")
    versions: List[DocumentVersionResponse] = Field(..., description="Document versions")
    total_versions: int = Field(..., description="Total number of versions")

# Create router
router = APIRouter(prefix="/api/v1/knowledge", tags=["Sales Knowledge Management"])

@router.post("/documents", response_model=DocumentResponse)
async def upload_document(
    request: DocumentUploadRequest,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Upload a new sales document (playbook, SOP, etc.) to the knowledge base.
    
    This endpoint stores sales documents with metadata and makes them searchable
    through semantic search capabilities.
    """
    try:
        request_id = str(uuid.uuid4())
        
        logger.info(
            f"Uploading document: {request.title} ({request.document_type})",
            extra={
                "request_id": request_id,
                "document_type": request.document_type,
                "title": request.title,
                "author": request.author,
                "version": request.version
            }
        )
        
        # Store document based on type
        if request.document_type == DocumentType.PLAYBOOK:
            doc_id = manager.store_playbook(
                title=request.title,
                content=request.content,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        elif request.document_type == DocumentType.SOP:
            doc_id = manager.store_sop(
                title=request.title,
                content=request.content,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        elif request.document_type == DocumentType.OBJECTION_HANDLING:
            doc_id = manager.store_objection_handling(
                title=request.title,
                content=request.content,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        elif request.document_type == DocumentType.QUALIFICATION_FRAMEWORK:
            doc_id = manager.store_qualification_framework(
                title=request.title,
                content=request.content,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        elif request.document_type == DocumentType.DEAL_PATTERN:
            doc_id = manager.store_successful_deal_pattern(
                title=request.title,
                content=request.content,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        else:
            # Use generic storage method for other types
            doc_id = manager._store_document(
                title=request.title,
                content=request.content,
                document_type=request.document_type,
                author=request.author,
                tags=request.tags,
                version=request.version
            )
        
        # Get the stored document for response
        stored_doc = manager.vector_store.get_document(doc_id)
        if not stored_doc:
            raise SalesKnowledgeException("Failed to retrieve stored document")
        
        log_business_event(
            logger,
            "document_uploaded",
            "sales_knowledge",
            doc_id,
            details={
                "document_type": request.document_type,
                "title": request.title,
                "version": request.version,
                "content_length": len(request.content)
            }
        )
        
        return _convert_to_document_response(stored_doc)
        
    except SalesKnowledgeException as e:
        logger.error(f"Knowledge management error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during document upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")

@router.get("/documents/{doc_id}", response_model=DocumentWithContentResponse)
async def get_document(
    doc_id: str,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Retrieve a specific document by ID with full content.
    """
    try:
        document = manager.vector_store.get_document(doc_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return _convert_to_document_with_content_response(document)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")

@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    request: DocumentUpdateRequest,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Update an existing document with version control.
    
    This creates a new version of the document while maintaining the version history.
    """
    try:
        request_id = str(uuid.uuid4())
        
        logger.info(
            f"Updating document {doc_id}",
            extra={
                "request_id": request_id,
                "doc_id": doc_id,
                "new_version": request.version
            }
        )
        
        new_doc_id = manager.update_document(
            doc_id=doc_id,
            title=request.title,
            content=request.content,
            tags=request.tags,
            version=request.version
        )
        
        # Get the updated document for response
        updated_doc = manager.vector_store.get_document(new_doc_id)
        if not updated_doc:
            raise SalesKnowledgeException("Failed to retrieve updated document")
        
        log_business_event(
            logger,
            "document_updated",
            "sales_knowledge",
            new_doc_id,
            details={
                "original_doc_id": doc_id,
                "new_version": request.version,
                "title_changed": request.title is not None,
                "content_changed": request.content is not None
            }
        )
        
        return _convert_to_document_response(updated_doc)
        
    except SalesKnowledgeException as e:
        logger.error(f"Knowledge management error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during document update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document update failed: {str(e)}")

@router.delete("/documents/{doc_id}", response_model=Dict[str, str])
async def delete_document(
    doc_id: str,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Delete a document from the knowledge base.
    """
    try:
        success = manager.delete_document(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        log_business_event(
            logger,
            "document_deleted",
            "sales_knowledge",
            doc_id
        )
        
        return {"message": "Document deleted successfully", "doc_id": doc_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Search for sales documents using semantic similarity.
    
    This endpoint performs semantic search across all sales documents and returns
    results ranked by similarity score.
    """
    try:
        import time
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        logger.info(
            f"Searching documents: {request.query[:50]}...",
            extra={
                "request_id": request_id,
                "query": request.query,
                "limit": request.limit,
                "document_types": request.document_types,
                "tags": request.tags
            }
        )
        
        # Perform search
        search_results = manager.search_similar(
            query=request.query,
            limit=request.limit,
            document_types=request.document_types,
            tags=request.tags
        )
        
        execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Convert results to response format
        response_results = []
        for result in search_results:
            doc_response = _convert_to_document_response(result.document)
            
            # Create content preview (first 200 characters)
            content_preview = result.document.content[:200]
            if len(result.document.content) > 200:
                content_preview += "..."
            
            response_results.append(SearchResultResponse(
                document=doc_response,
                similarity_score=result.similarity_score,
                content_preview=content_preview
            ))
        
        log_business_event(
            logger,
            "document_search_performed",
            "sales_knowledge",
            request_id,
            details={
                "query": request.query,
                "results_count": len(search_results),
                "execution_time_ms": execution_time
            }
        )
        
        return SearchResponse(
            results=response_results,
            total_results=len(search_results),
            query=request.query,
            execution_time_ms=execution_time
        )
        
    except SalesKnowledgeException as e:
        logger.error(f"Knowledge search error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/context", response_model=SalesContextResponse)
async def get_sales_context(
    request: SalesContextRequest,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Retrieve comprehensive sales context for decision-making.
    
    This endpoint provides relevant sales guidance, playbooks, and methodologies
    based on the decision type and context.
    """
    try:
        request_id = str(uuid.uuid4())
        
        logger.info(
            f"Retrieving sales context for: {request.decision_type}",
            extra={
                "request_id": request_id,
                "decision_type": request.decision_type,
                "additional_context": request.additional_context
            }
        )
        
        # Get sales context
        context = manager.get_sales_context(
            decision_type=request.decision_type,
            additional_context=request.additional_context
        )
        
        # Convert to response format
        response = SalesContextResponse(
            relevant_playbooks=[_convert_sales_doc_to_response(doc) for doc in context.relevant_playbooks],
            objection_handling=[_convert_sales_doc_to_response(doc) for doc in context.objection_handling],
            successful_patterns=[_convert_sales_doc_to_response(doc) for doc in context.successful_patterns],
            methodologies=[_convert_sales_doc_to_response(doc) for doc in context.methodologies],
            confidence_score=context.confidence_score,
            query=context.query,
            retrieved_at=context.retrieved_at
        )
        
        log_business_event(
            logger,
            "sales_context_retrieved",
            "sales_knowledge",
            request_id,
            details={
                "decision_type": request.decision_type,
                "confidence_score": context.confidence_score,
                "total_documents": (
                    len(context.relevant_playbooks) + 
                    len(context.objection_handling) + 
                    len(context.successful_patterns) + 
                    len(context.methodologies)
                )
            }
        )
        
        return response
        
    except SalesKnowledgeException as e:
        logger.error(f"Knowledge context error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during context retrieval: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Context retrieval failed: {str(e)}")

@router.get("/documents/{doc_id}/versions", response_model=DocumentVersionsResponse)
async def get_document_versions(
    doc_id: str,
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Get all versions of a document for version control.
    """
    try:
        versions = manager.get_document_versions(doc_id)
        
        version_responses = [
            DocumentVersionResponse(
                id=version["id"],
                version=version["version"],
                title=version["title"],
                created_at=version["created_at"],
                updated_at=version["updated_at"],
                is_active=version["is_active"],
                author=version["author"]
            )
            for version in versions
        ]
        
        return DocumentVersionsResponse(
            base_document_id=doc_id,
            versions=version_responses,
            total_versions=len(version_responses)
        )
        
    except Exception as e:
        logger.error(f"Failed to get versions for document {doc_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document versions: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_knowledge_stats(
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Get statistics about the knowledge base.
    """
    try:
        total_documents = manager.get_document_count()
        
        # Get document type distribution (simplified for now)
        stats = {
            "total_documents": total_documents,
            "document_types": {doc_type.value: 0 for doc_type in DocumentType},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

@router.get("/health", response_model=Dict[str, Any])
async def health_check(
    manager: SalesKnowledgeManager = Depends(get_knowledge_manager)
):
    """
    Perform a health check of the knowledge management system.
    """
    try:
        # Basic health checks
        total_docs = manager.get_document_count()
        
        health_info = {
            "status": "healthy",
            "service": "sales_knowledge_management",
            "total_documents": total_docs,
            "vector_store_connected": True,  # Simplified check
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return health_info
        
    except Exception as e:
        logger.error(f"Knowledge health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

# Helper functions
def _convert_to_document_response(document) -> DocumentResponse:
    """Convert vector store document to API response format."""
    # Convert comma-separated tags back to list
    tags_str = document.metadata.get("tags", "")
    tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []
    
    return DocumentResponse(
        id=document.id,
        title=document.metadata.get("title", "Untitled"),
        document_type=DocumentType(document.metadata.get("document_type", "playbook")),
        version=document.metadata.get("version", "1.0"),
        author=document.metadata.get("author"),
        tags=tags,
        created_at=datetime.fromisoformat(document.metadata["created_at"]) if document.metadata.get("created_at") else datetime.utcnow(),
        updated_at=datetime.fromisoformat(document.metadata["updated_at"]) if document.metadata.get("updated_at") else datetime.utcnow(),
        is_active=document.metadata.get("is_active", "true") == "true"
    )

def _convert_to_document_with_content_response(document) -> DocumentWithContentResponse:
    """Convert vector store document to API response format with content."""
    base_response = _convert_to_document_response(document)
    
    return DocumentWithContentResponse(
        id=base_response.id,
        title=base_response.title,
        document_type=base_response.document_type,
        version=base_response.version,
        author=base_response.author,
        tags=base_response.tags,
        created_at=base_response.created_at,
        updated_at=base_response.updated_at,
        is_active=base_response.is_active,
        content=document.content
    )

def _convert_sales_doc_to_response(sales_doc: SalesDocument) -> DocumentResponse:
    """Convert SalesDocument to API response format."""
    return DocumentResponse(
        id=sales_doc.id,
        title=sales_doc.title,
        document_type=sales_doc.document_type,
        version=sales_doc.version,
        author=sales_doc.author,
        tags=sales_doc.tags,
        created_at=sales_doc.created_at,
        updated_at=sales_doc.updated_at,
        is_active=sales_doc.is_active
    )