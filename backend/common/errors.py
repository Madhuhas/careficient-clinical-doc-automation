"""
Custom exceptions and error handling for Careficient pipelines.
"""

from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes."""
    # General errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # File/Document errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    DOCUMENT_PROCESSING_ERROR = "DOCUMENT_PROCESSING_ERROR"
    
    # Audio pipeline errors
    AUDIO_PROCESSING_ERROR = "AUDIO_PROCESSING_ERROR"
    TRANSCRIPTION_ERROR = "TRANSCRIPTION_ERROR"
    AUDIO_FORMAT_ERROR = "AUDIO_FORMAT_ERROR"
    
    # OCR pipeline errors
    OCR_ERROR = "OCR_ERROR"
    PDF_PROCESSING_ERROR = "PDF_PROCESSING_ERROR"
    IMAGE_PROCESSING_ERROR = "IMAGE_PROCESSING_ERROR"
    
    # Extraction errors
    EXTRACTION_ERROR = "EXTRACTION_ERROR"
    CLINICAL_EXTRACTION_ERROR = "CLINICAL_EXTRACTION_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    
    # Model/API errors
    MODEL_LOADING_ERROR = "MODEL_LOADING_ERROR"
    MODEL_INFERENCE_ERROR = "MODEL_INFERENCE_ERROR"
    API_ERROR = "API_ERROR"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    QUERY_ERROR = "QUERY_ERROR"
    
    # AWS errors
    AWS_ERROR = "AWS_ERROR"
    S3_ERROR = "S3_ERROR"


class CareficentException(Exception):
    """
    Base exception for all Careficient errors.
    
    Provides structured error information with codes, messages, and details.
    """
    
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        Initialize exception.
        
        Args:
            message: Error message
            error_code: Standard error code
            status_code: HTTP status code
            details: Additional error details
            cause: Original exception (for chaining)
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary."""
        return {
            "error": self.error_code.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"[{self.error_code.value}] {self.message}"


class ValidationError(CareficentException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
        """
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=message,
            error_code=ErrorCode.DATA_VALIDATION_ERROR,
            status_code=422,
            details=details
        )


class FileError(CareficentException):
    """Raised for file-related errors."""
    
    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.FILE_NOT_FOUND,
    ):
        """
        Initialize file error.
        
        Args:
            message: Error message
            filename: Name of problematic file
            error_code: Specific error code
        """
        details = {}
        if filename:
            details["filename"] = filename
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class DocumentError(CareficentException):
    """Raised for document processing errors."""
    
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        document_type: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.DOCUMENT_PROCESSING_ERROR,
    ):
        """
        Initialize document error.
        
        Args:
            message: Error message
            document_id: ID of document
            document_type: Type of document
            error_code: Specific error code
        """
        details = {}
        if document_id:
            details["document_id"] = document_id
        if document_type:
            details["document_type"] = document_type
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class AudioError(CareficentException):
    """Raised for audio processing errors."""
    
    def __init__(
        self,
        message: str,
        audio_file: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.AUDIO_PROCESSING_ERROR,
    ):
        """
        Initialize audio error.
        
        Args:
            message: Error message
            audio_file: Name of audio file
            error_code: Specific error code
        """
        details = {}
        if audio_file:
            details["audio_file"] = audio_file
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class OCRError(CareficentException):
    """Raised for OCR processing errors."""
    
    def __init__(
        self,
        message: str,
        page_number: Optional[int] = None,
        error_code: ErrorCode = ErrorCode.OCR_ERROR,
    ):
        """
        Initialize OCR error.
        
        Args:
            message: Error message
            page_number: Page that failed OCR
            error_code: Specific error code
        """
        details = {}
        if page_number is not None:
            details["page_number"] = page_number
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class ExtractionError(CareficentException):
    """Raised for clinical data extraction errors."""
    
    def __init__(
        self,
        message: str,
        extraction_type: Optional[str] = None,
        confidence: Optional[float] = None,
        error_code: ErrorCode = ErrorCode.EXTRACTION_ERROR,
    ):
        """
        Initialize extraction error.
        
        Args:
            message: Error message
            extraction_type: Type of extraction (vitals, meds, etc.)
            confidence: Confidence score if available
            error_code: Specific error code
        """
        details = {}
        if extraction_type:
            details["extraction_type"] = extraction_type
        if confidence is not None:
            details["confidence"] = confidence
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class ModelError(CareficentException):
    """Raised for model-related errors."""
    
    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.MODEL_LOADING_ERROR,
    ):
        """
        Initialize model error.
        
        Args:
            message: Error message
            model_name: Name of model
            error_code: Specific error code
        """
        details = {}
        if model_name:
            details["model_name"] = model_name
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details
        )


class DatabaseError(CareficentException):
    """Raised for database errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.DATABASE_ERROR,
    ):
        """
        Initialize database error.
        
        Args:
            message: Error message
            operation: Database operation (query, insert, update, etc.)
            error_code: Specific error code
        """
        details = {}
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details
        )


class AWSError(CareficentException):
    """Raised for AWS-related errors."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        resource: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.AWS_ERROR,
    ):
        """
        Initialize AWS error.
        
        Args:
            message: Error message
            service: AWS service (s3, lambda, etc.)
            resource: Resource identifier
            error_code: Specific error code
        """
        details = {}
        if service:
            details["service"] = service
        if resource:
            details["resource"] = resource
        
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=details
        )


class NotFoundError(CareficentException):
    """Raised when resource not found."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize not found error.
        
        Args:
            message: Error message
            resource_type: Type of resource (document, transcript, etc.)
            resource_id: ID of resource
        """
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


# Error handling utilities

def handle_exception(
    exception: Exception,
    context: Optional[str] = None,
    logger=None
) -> Dict[str, Any]:
    """
    Convert exception to error response dictionary.
    
    Args:
        exception: Exception to handle
        context: Optional context string
        logger: Optional logger for error logging
    
    Returns:
        Error response dictionary
    """
    if logger:
        logger.error(f"Exception: {exception}", exc_info=True)
    
    if isinstance(exception, CareficentException):
        return exception.to_dict()
    
    # Convert generic exceptions to CareficentException
    error = CareficentException(
        message=str(exception),
        error_code=ErrorCode.INTERNAL_ERROR,
        status_code=500,
        cause=exception
    )
    
    if context:
        error.details["context"] = context
    
    return error.to_dict()
