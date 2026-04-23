"""
Common utilities module for Careficient pipelines.
Provides shared code for logging, error handling, validation, and AWS integration.
"""

__version__ = "1.0.0"
__author__ = "Careficient Team"

# Utilities
from .utils import (
    save_json,
    load_json,
    save_text,
    load_text,
    validate_model,
    validate_model_safe,
    generate_id,
    generate_patient_id,
    generate_document_id,
    generate_extraction_id,
    generate_transcript_id,
    time_operation,
    get_timestamp,
    format_confidence,
    truncate_text,
    sanitize_filename,
    flatten_dict,
    chunk_list,
    get_env,
    model_to_dict,
    dict_to_model,
    update_model,
    ProcessingStatus,
    DocumentType,
    ExtractionType,
)

# Logging
from .logging_config import (
    setup_logging,
    log_with_data,
    LogContext,
    get_logger,
    configure_pipeline_logging,
)

# Error handling
from .errors import (
    CareficentException,
    ValidationError,
    FileError,
    DocumentError,
    AudioError,
    OCRError,
    ExtractionError,
    ModelError,
    DatabaseError,
    AWSError,
    NotFoundError,
    ErrorCode,
    handle_exception,
)

# Database
from .database import (
    DatabaseConnection,
    PostgreSQLConnection,
    SQLiteConnection,
    MongoDBConnection,
    DatabaseFactory,
    DatabaseType,
    QueryBuilder,
    DATABASE_SCHEMAS,
)

# AWS
from .aws_utils import (
    S3Manager,
    LambdaManager,
    StepFunctionsManager,
    DynamoDBManager,
    AWSConfig,
)

__all__ = [
    # Utilities
    "save_json",
    "load_json",
    "save_text",
    "load_text",
    "validate_model",
    "validate_model_safe",
    "generate_id",
    "generate_patient_id",
    "generate_document_id",
    "generate_extraction_id",
    "generate_transcript_id",
    "time_operation",
    "get_timestamp",
    "format_confidence",
    "truncate_text",
    "sanitize_filename",
    "flatten_dict",
    "chunk_list",
    "get_env",
    "model_to_dict",
    "dict_to_model",
    "update_model",
    "ProcessingStatus",
    "DocumentType",
    "ExtractionType",
    # Logging
    "setup_logging",
    "log_with_data",
    "LogContext",
    "get_logger",
    "configure_pipeline_logging",
    # Errors
    "CareficentException",
    "ValidationError",
    "FileError",
    "DocumentError",
    "AudioError",
    "OCRError",
    "ExtractionError",
    "ModelError",
    "DatabaseError",
    "AWSError",
    "NotFoundError",
    "ErrorCode",
    "handle_exception",
    # Database
    "DatabaseConnection",
    "PostgreSQLConnection",
    "SQLiteConnection",
    "MongoDBConnection",
    "DatabaseFactory",
    "DatabaseType",
    "QueryBuilder",
    "DATABASE_SCHEMAS",
    # AWS
    "S3Manager",
    "LambdaManager",
    "StepFunctionsManager",
    "DynamoDBManager",
    "AWSConfig",
]
