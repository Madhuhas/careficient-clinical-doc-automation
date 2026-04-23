"""
Audio Pipeline Module
Handles clinical audio transcription and structured data extraction.
"""

__version__ = "1.0.0"
__author__ = "Careficient Team"

from .app import app
from .models import (
    VitalSign,
    Medication,
    Symptom,
    Assessment,
    ClinicalExtract,
    OASISPrefill,
)
from .extractor import ClinicalExtractor

__all__ = [
    "app",
    "VitalSign",
    "Medication",
    "Symptom",
    "Assessment",
    "ClinicalExtract",
    "OASISPrefill",
    "ClinicalExtractor",
]

