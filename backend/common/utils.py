"""
Common utility functions used across all pipelines.
Includes logging, error handling, validation, and file operations.
"""

import json
import logging
import os
import uuid
from typing import Dict, Any, Optional, List, TypeVar, Generic, Type
from datetime import datetime
from pathlib import Path
from enum import Enum
from functools import wraps
import time

from pydantic import BaseModel, ValidationError, ConfigDict


logger = logging.getLogger(__name__)


# Type variables for generics
T = TypeVar('T', bound=BaseModel)


class ProcessingStatus(str, Enum):
    """Standard processing statuses."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class DocumentType(str, Enum):
    """Supported document types."""
    AUDIO = "audio"
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"


class ExtractionType(str, Enum):
    """Types of clinical data extraction."""
    VITALS = "vitals"
    MEDICATIONS = "medications"
    SYMPTOMS = "symptoms"
    ASSESSMENTS = "assessments"
    ALL = "all"


# ============================================================================
# File Operations
# ============================================================================

def save_json(data: Dict[str, Any], path: str, indent: int = 2) -> bool:
    """
    Save data as JSON file.
    
    Args:
        data: Data to save
        path: File path
        indent: JSON indentation level
    
    Returns:
        True if successful, False otherwise
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)
        logger.debug(f"Saved JSON to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {path}: {e}")
        return False


def load_json(path: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file.
    
    Args:
        path: File path
    
    Returns:
        Loaded data or None if error
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        logger.debug(f"Loaded JSON from {path}")
        return data
    except Exception as e:
        logger.error(f"Failed to load JSON from {path}: {e}")
        return None


def save_text(content: str, path: str) -> bool:
    """
    Save text content to file.
    
    Args:
        content: Text content
        path: File path
    
    Returns:
        True if successful
    """
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        logger.debug(f"Saved text to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save text to {path}: {e}")
        return False


def load_text(path: str) -> Optional[str]:
    """
    Load text content from file.
    
    Args:
        path: File path
    
    Returns:
        Text content or None if error
    """
    try:
        with open(path, 'r') as f:
            content = f.read()
        logger.debug(f"Loaded text from {path}")
        return content
    except Exception as e:
        logger.error(f"Failed to load text from {path}: {e}")
        return None


# ============================================================================
# Validation
# ============================================================================

def validate_model(model_cls: Type[T], data: Dict[str, Any]) -> T:
    """
    Validate data against a Pydantic model.
    
    Args:
        model_cls: Pydantic model class
        data: Data to validate
    
    Returns:
        Validated model instance
    
    Raises:
        ValidationError: If validation fails
    """
    try:
        return model_cls(**data)
    except ValidationError as e:
        logger.error(f"Validation error for {model_cls.__name__}: {e}")
        raise


def validate_model_safe(model_cls: Type[T], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely validate data, returning error dict if invalid.
    
    Args:
        model_cls: Pydantic model class
        data: Data to validate
    
    Returns:
        Dict with 'success' and 'data' or 'error'
    """
    try:
        model = validate_model(model_cls, data)
        return {
            "success": True,
            "data": model.model_dump(),
            "message": "Validation successful"
        }
    except ValidationError as e:
        return {
            "success": False,
            "error": str(e),
            "data": data,
            "message": "Validation failed"
        }


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate data against a JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        from jsonschema import validate, ValidationError
        validate(instance=data, schema=schema)
        return True, None
    except ImportError:
        logger.warning("jsonschema not installed, skipping validation")
        return True, None
    except ValidationError as e:
        error_msg = f"Schema validation failed: {e.message}"
        logger.error(error_msg)
        return False, error_msg


# ============================================================================
# IDs and Keys
# ============================================================================

def generate_id(prefix: str = "") -> str:
    """
    Generate a unique ID.
    
    Args:
        prefix: Optional prefix
    
    Returns:
        Unique ID string
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}_{unique_id}" if prefix else unique_id


def generate_patient_id() -> str:
    """Generate a unique patient ID."""
    return generate_id("P")


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return generate_id("DOC")


def generate_extraction_id() -> str:
    """Generate a unique extraction ID."""
    return generate_id("EXT")


def generate_transcript_id() -> str:
    """Generate a unique transcript ID."""
    return generate_id("TRX")


# ============================================================================
# Timing and Performance
# ============================================================================

def time_operation(operation_name: str):
    """
    Decorator to time operation execution.
    
    Args:
        operation_name: Name for logging
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            logger.debug(f"Starting {operation_name}...")
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"{operation_name} completed in {elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"{operation_name} failed after {elapsed:.2f}s: {e}")
                raise
        return wrapper
    return decorator


def get_timestamp() -> str:
    """Get current ISO timestamp."""
    return datetime.utcnow().isoformat()


def timestamp_to_datetime(timestamp: str) -> Optional[datetime]:
    """Convert ISO timestamp string to datetime."""
    try:
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except Exception as e:
        logger.error(f"Failed to parse timestamp {timestamp}: {e}")
        return None


# ============================================================================
# Data Formatting
# ============================================================================

def format_confidence(score: float) -> str:
    """
    Format confidence score as percentage.
    
    Args:
        score: Confidence score (0-1)
    
    Returns:
        Formatted string like "87.5%"
    """
    return f"{score * 100:.1f}%"


def confidence_level(score: float) -> str:
    """
    Get confidence level description.
    
    Args:
        score: Confidence score (0-1)
    
    Returns:
        "Very Low", "Low", "Medium", "High", "Very High"
    """
    if score >= 0.95:
        return "Very High"
    elif score >= 0.75:
        return "High"
    elif score >= 0.5:
        return "Medium"
    elif score >= 0.25:
        return "Low"
    else:
        return "Very Low"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix for truncated text
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe filesystem usage.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip('. ')
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    return sanitized if sanitized else "file"


# ============================================================================
# Collections and Transformations
# ============================================================================

def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict:
    """
    Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for recursion
        sep: Separator for keys
    
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_dict(item, f"{new_key}[{i}]", sep=sep).items())
                else:
                    items.append((f"{new_key}[{i}]", item))
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
    
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_list(lst: List[str], case_sensitive: bool = False) -> List[str]:
    """
    Remove duplicates from list while preserving order.
    
    Args:
        lst: List to deduplicate
        case_sensitive: Whether to treat "Foo" and "foo" as same
    
    Returns:
        Deduplicated list
    """
    seen = set()
    result = []
    for item in lst:
        key = item if case_sensitive else item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ============================================================================
# Environment
# ============================================================================

def get_env(key: str, default: Any = None, required: bool = False) -> Any:
    """
    Get environment variable with type conversion.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raise error if not found
    
    Returns:
        Environment variable value
    
    Raises:
        RuntimeError: If required and not found
    """
    value = os.getenv(key, default)
    
    if value is None and required:
        raise RuntimeError(f"Required environment variable {key} not found")
    
    # Type conversion
    if value is not None:
        if value.lower() in ["true", "yes", "1"]:
            return True
        elif value.lower() in ["false", "no", "0"]:
            return False
        elif value.isdigit():
            return int(value)
    
    return value


def get_project_root() -> Path:
    """Get project root directory."""
    return Path(__file__).parent.parent.parent


def get_backend_root() -> Path:
    """Get backend directory."""
    return Path(__file__).parent.parent


# ============================================================================
# Pydantic Helpers
# ============================================================================

def model_to_dict(model: BaseModel, include: Optional[set] = None, exclude: Optional[set] = None) -> Dict:
    """
    Convert Pydantic model to dict with optional field filtering.
    
    Args:
        model: Pydantic model instance
        include: Fields to include
        exclude: Fields to exclude
    
    Returns:
        Dictionary representation
    """
    return model.model_dump(include=include, exclude=exclude)


def dict_to_model(model_cls: Type[T], data: Dict[str, Any]) -> T:
    """
    Convert dictionary to Pydantic model.
    
    Args:
        model_cls: Pydantic model class
        data: Dictionary data
    
    Returns:
        Model instance
    """
    return model_cls(**data)


def update_model(model: T, update_data: Dict[str, Any]) -> T:
    """
    Update Pydantic model with new data.
    
    Args:
        model: Existing model instance
        update_data: Data to update
    
    Returns:
        Updated model instance
    """
    model_dict = model.model_dump()
    model_dict.update(update_data)
    return type(model)(**model_dict)


# ============================================================================
# Error Messages
# ============================================================================

def format_error(error: Exception, include_traceback: bool = False) -> str:
    """
    Format error message for logging.
    
    Args:
        error: Exception
        include_traceback: Whether to include traceback
    
    Returns:
        Formatted error message
    """
    msg = f"{type(error).__name__}: {str(error)}"
    
    if include_traceback:
        import traceback
        msg += "\n" + traceback.format_exc()
    
    return msg

