"""
OCR Pipeline Module
Handles document OCR and clinical data extraction from scanned documents and PDFs.
"""

__version__ = "1.0.0"
__author__ = "Careficient Team"

from .app import app
from .models import (
    OCRDocument,
    OCRPage,
    OCRClinicalExtract,
    OCRBatch,
    OCRUploadResponse,
    OCRExtractionResponse,
)
from .extractor import OCRExtractor

__all__ = [
    "app",
    "OCRDocument",
    "OCRPage",
    "OCRClinicalExtract",
    "OCRBatch",
    "OCRUploadResponse",
    "OCRExtractionResponse",
    "OCRExtractor",
]
