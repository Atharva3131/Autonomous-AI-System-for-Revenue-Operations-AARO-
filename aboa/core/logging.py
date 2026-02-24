"""
Structured logging configuration for ABOA system.
"""

import logging
import logging.config
import sys
from typing import Any, Dict, Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "getMessage", "exc_info",
                "exc_text", "stack_info"
            }:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class TextFormatter(logging.Formatter):
    """Custom text formatter with consistent structure."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(log_level: str = "INFO", log_format: str = "json", log_file: Optional[str] = None) -> None:
    """
    Setup structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_file: Optional file path for log output
    """
    # Choose formatter based on format type
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup handlers list
    handlers = [console_handler]
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers,
        force=True
    )
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name."""
    return logging.getLogger(name)


def log_business_event(
    logger: logging.Logger,
    event_type: str,
    entity_type: str,
    entity_id: str,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None
) -> None:
    """
    Log a business event with structured data.
    
    Args:
        logger: Logger instance
        event_type: Type of business event (e.g., 'decision_made', 'action_executed')
        entity_type: Type of business entity (e.g., 'lead', 'deal', 'ticket')
        entity_id: Unique identifier for the entity
        details: Additional event details
        user_id: Optional user identifier
    """
    logger.info(
        f"Business event: {event_type}",
        extra={
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "user_id": user_id,
            "component": "business_events"
        }
    )


def log_system_event(
    logger: logging.Logger,
    event_type: str,
    component: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[Exception] = None
) -> None:
    """
    Log a system event with structured data.
    
    Args:
        logger: Logger instance
        event_type: Type of system event (e.g., 'startup', 'shutdown', 'error')
        component: System component name
        details: Additional event details
        error: Optional exception information
    """
    if error:
        logger.error(
            f"System event: {event_type}",
            extra={
                "event_type": event_type,
                "component": component,
                "details": details or {},
                "error_type": type(error).__name__,
                "error_message": str(error)
            },
            exc_info=error
        )
    else:
        logger.info(
            f"System event: {event_type}",
            extra={
                "event_type": event_type,
                "component": component,
                "details": details or {}
            }
        )