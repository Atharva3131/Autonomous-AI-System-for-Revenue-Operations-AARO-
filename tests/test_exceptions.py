"""
Tests for exception handling.
"""

import pytest
from aboa.core.exceptions import (
    ABOAException,
    DataIngestionError,
    DataValidationError,
    RetryableError,
    NonRetryableError,
    handle_exception
)


def test_aboa_exception_creation():
    """Test ABOA exception creation and serialization."""
    error = ABOAException(
        message="Test error",
        error_code="TEST_ERROR",
        details={"key": "value"}
    )
    
    assert error.message == "Test error"
    assert error.error_code == "TEST_ERROR"
    assert error.details == {"key": "value"}
    
    error_dict = error.to_dict()
    assert error_dict["error_code"] == "TEST_ERROR"
    assert error_dict["message"] == "Test error"
    assert error_dict["details"] == {"key": "value"}
    assert error_dict["type"] == "ABOAException"


def test_specific_exception_types():
    """Test specific exception types."""
    data_error = DataIngestionError("Data ingestion failed")
    assert isinstance(data_error, ABOAException)
    assert data_error.error_code == "DataIngestionError"
    
    validation_error = DataValidationError("Validation failed")
    assert isinstance(validation_error, ABOAException)
    assert validation_error.error_code == "DataValidationError"


def test_retryable_error():
    """Test retryable error with retry parameters."""
    error = RetryableError(
        message="Temporary failure",
        retry_after=30,
        max_retries=3
    )
    
    assert error.retry_after == 30
    assert error.max_retries == 3
    assert isinstance(error, ABOAException)


def test_handle_exception_no_reraise():
    """Test exception handling without reraising."""
    error = ValueError("Test error")
    context = {"operation": "test"}
    
    result = handle_exception(error, context, reraise=False)
    
    assert result is not None
    assert result["error_type"] == "ValueError"
    assert result["error_message"] == "Test error"
    assert result["context"] == context


def test_handle_exception_with_reraise():
    """Test exception handling with reraising."""
    error = ValueError("Test error")
    
    with pytest.raises(ValueError):
        handle_exception(error, reraise=True)