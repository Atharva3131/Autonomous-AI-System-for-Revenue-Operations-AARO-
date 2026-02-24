"""
Base exception classes and error handling utilities for ABOA system.
"""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)


class ABOAException(Exception):
    """Base exception class for all ABOA-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


class DataIngestionError(ABOAException):
    """Raised when data ingestion operations fail."""
    pass


class DataValidationError(ABOAException):
    """Raised when data validation fails."""
    pass


class KnowledgeManagerError(ABOAException):
    """Raised when knowledge management operations fail."""
    pass


class DecisionEngineError(ABOAException):
    """Raised when decision engine operations fail."""
    pass


class ActionExecutionError(ABOAException):
    """Raised when action execution fails."""
    pass


class HumanLoopError(ABOAException):
    """Raised when human-in-the-loop operations fail."""
    pass


class ConfigurationError(ABOAException):
    """Raised when configuration is invalid or missing."""
    pass


class ExternalIntegrationError(ABOAException):
    """Raised when external system integration fails."""
    pass


class IntegrationError(ABOAException):
    """Raised when integration operations fail."""
    pass


class BusinessRuleViolationError(ABOAException):
    """Raised when business rules are violated."""
    pass


class RetryableError(ABOAException):
    """Base class for errors that can be retried."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        max_retries: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        self.max_retries = max_retries


class NonRetryableError(ABOAException):
    """Base class for errors that should not be retried."""
    pass


def handle_exception(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Handle exceptions with proper logging and context.
    
    Args:
        error: The exception to handle
        context: Additional context information
        reraise: Whether to reraise the exception after handling
    
    Returns:
        Error details dictionary if not reraising
    """
    error_details = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    if isinstance(error, ABOAException):
        error_details.update(error.to_dict())
        logger.error(
            f"ABOA error: {error.message}",
            extra={
                "error_code": error.error_code,
                "error_details": error.details,
                "context": context
            },
            exc_info=error.cause
        )
    else:
        logger.error(
            f"Unexpected error: {str(error)}",
            extra={"context": context},
            exc_info=error
        )
    
    if reraise:
        raise error
    
    return error_details


async def aboa_exception_handler(request: Request, exc: ABOAException) -> JSONResponse:
    """Handle ABOA-specific exceptions."""
    logger.error(
        f"ABOA exception in {request.method} {request.url}: {exc.message}",
        extra={
            "error_code": exc.error_code,
            "error_details": exc.details,
            "request_path": str(request.url),
            "request_method": request.method
        }
    )
    
    # Determine HTTP status code based on exception type
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, DataValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, ConfigurationError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    elif isinstance(exc, ExternalIntegrationError):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, BusinessRuleViolationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors."""
    logger.warning(
        f"Validation error in {request.method} {request.url}: {exc.errors()}",
        extra={
            "validation_errors": exc.errors(),
            "request_path": str(request.url),
            "request_method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"validation_errors": exc.errors()},
            "type": "RequestValidationError"
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        f"HTTP exception in {request.method} {request.url}: {exc.detail}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_path": str(request.url),
            "request_method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {},
            "type": "HTTPException"
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(
        f"Unexpected exception in {request.method} {request.url}: {str(exc)}",
        extra={
            "request_path": str(request.url),
            "request_method": request.method
        },
        exc_info=exc
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
            "type": "InternalServerError"
        }
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application."""
    app.add_exception_handler(ABOAException, aboa_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)