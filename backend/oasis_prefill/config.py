"""
Configuration for OASIS Prefill module.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Form Configuration
DEFAULT_FORM_VERSION = os.getenv("OASIS_FORM_VERSION", "E1")
ENABLE_E2 = os.getenv("OASIS_ENABLE_E2", "true").lower() == "true"

# Confidence Thresholds
MIN_CONFIDENCE_FOR_VALID = float(os.getenv("OASIS_MIN_CONFIDENCE_VALID", "0.50"))
MIN_CONFIDENCE_FOR_PARTIAL = float(os.getenv("OASIS_MIN_CONFIDENCE_PARTIAL", "0.25"))

# Field Requirements
MIN_FIELDS_FOR_VALID = int(os.getenv("OASIS_MIN_FIELDS_VALID", "25"))
MIN_FIELDS_FOR_PARTIAL = int(os.getenv("OASIS_MIN_FIELDS_PARTIAL", "12"))

# Weights for confidence calculation
EXTRACTION_CONFIDENCE_WEIGHT = float(os.getenv("OASIS_EXTRACTION_WEIGHT", "0.6"))
FIELD_FILL_WEIGHT = float(os.getenv("OASIS_FIELD_FILL_WEIGHT", "0.4"))

# Database Configuration (optional)
USE_DATABASE = os.getenv("OASIS_USE_DATABASE", "false").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///oasis.db")

# AWS Configuration (optional)
USE_AWS = os.getenv("OASIS_USE_AWS", "false").lower() == "true"
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "oasis-forms")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Logging Configuration
LOG_LEVEL = os.getenv("OASIS_LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("OASIS_LOG_FILE", "oasis.log")

# API Configuration
API_PORT = int(os.getenv("OASIS_API_PORT", "8003"))
API_HOST = os.getenv("OASIS_API_HOST", "0.0.0.0")
DEBUG_MODE = os.getenv("OASIS_DEBUG", "false").lower() == "true"

# Batch Processing
BATCH_SIZE = int(os.getenv("OASIS_BATCH_SIZE", "10"))
MAX_BATCH_SIZE = int(os.getenv("OASIS_MAX_BATCH_SIZE", "100"))
BATCH_TIMEOUT_SECONDS = int(os.getenv("OASIS_BATCH_TIMEOUT", "300"))

# Field Mapping Configuration
CUSTOM_MAPPINGS_FILE = os.getenv("OASIS_CUSTOM_MAPPINGS", None)

# CMS/Compliance
CMS_VALIDATION_ENABLED = os.getenv("OASIS_CMS_VALIDATION", "true").lower() == "true"
AUDIT_TRAIL_ENABLED = os.getenv("OASIS_AUDIT_TRAIL", "true").lower() == "true"

# Summary
CONFIG = {
    "form_version": DEFAULT_FORM_VERSION,
    "enable_e2": ENABLE_E2,
    "min_confidence_valid": MIN_CONFIDENCE_FOR_VALID,
    "min_confidence_partial": MIN_CONFIDENCE_FOR_PARTIAL,
    "min_fields_valid": MIN_FIELDS_FOR_VALID,
    "min_fields_partial": MIN_FIELDS_FOR_PARTIAL,
    "extraction_weight": EXTRACTION_CONFIDENCE_WEIGHT,
    "field_fill_weight": FIELD_FILL_WEIGHT,
    "use_database": USE_DATABASE,
    "database_url": DATABASE_URL,
    "use_aws": USE_AWS,
    "aws_bucket": AWS_S3_BUCKET,
    "aws_region": AWS_REGION,
    "log_level": LOG_LEVEL,
    "log_file": LOG_FILE,
    "api_port": API_PORT,
    "api_host": API_HOST,
    "debug": DEBUG_MODE,
    "batch_size": BATCH_SIZE,
    "max_batch_size": MAX_BATCH_SIZE,
    "batch_timeout": BATCH_TIMEOUT_SECONDS,
    "cms_validation": CMS_VALIDATION_ENABLED,
    "audit_trail": AUDIT_TRAIL_ENABLED,
}
