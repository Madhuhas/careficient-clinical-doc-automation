"""
Pydantic models for OCR pipeline.
Extends audio pipeline models for document-based clinical data extraction.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Re-export audio models for consistency
try:
    from audio_pipeline.models import VitalSign, Medication, Symptom, Assessment, ClinicalExtract
except ImportError:
    # Fallback for standalone testing
    from pydantic import BaseModel
    
    class VitalSign(BaseModel):
        name: str
        value: str
        unit: Optional[str] = None
    
    class Medication(BaseModel):
        name: str
        dosage: Optional[str] = None
        frequency: Optional[str] = None
        route: Optional[str] = None
        status: Optional[str] = None
    
    class Symptom(BaseModel):
        name: str
        severity: Optional[str] = None
        duration: Optional[str] = None
        location: Optional[str] = None
    
    class Assessment(BaseModel):
        condition: str
        notes: Optional[str] = None
    
    class ClinicalExtract(BaseModel):
        vitals: List[VitalSign] = Field(default_factory=list)
        medications: List[Medication] = Field(default_factory=list)
        symptoms: List[Symptom] = Field(default_factory=list)
        assessments: List[Assessment] = Field(default_factory=list)
        raw_transcript: str


class OCRPage(BaseModel):
    """Represents a single page of OCR'd document."""
    page_number: int = Field(..., description="Page number (1-indexed)")
    raw_text: str = Field(..., description="Raw OCR'd text from page")
    confidence: float = Field(..., description="OCR confidence for this page (0-1)")
    text_blocks: List[str] = Field(default_factory=list, description="Text grouped by blocks/regions")
    detected_tables: List[Dict[str, Any]] = Field(default_factory=list, description="Tables detected on page")
    detected_forms: List[Dict[str, str]] = Field(default_factory=list, description="Form fields detected")


class OCRDocument(BaseModel):
    """Represents a complete OCR'd document."""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original document filename")
    file_type: str = Field(..., description="File type (pdf, jpg, png, tiff)")
    pages: List[OCRPage] = Field(..., description="List of OCR'd pages")
    total_pages: int = Field(..., description="Total number of pages")
    raw_full_text: str = Field(..., description="Full concatenated text from all pages")
    overall_confidence: float = Field(..., description="Average confidence score across all pages")
    detected_document_type: Optional[str] = Field(None, description="Type (vital sheet, medication list, assessment, etc.)")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_seconds: Optional[float] = Field(None, description="Time to process document")


class OCRClinicalExtract(ClinicalExtract):
    """Clinical data extracted from OCR'd document."""
    extraction_id: str = Field(..., description="Unique extraction identifier")
    document_id: str = Field(..., description="Source document ID")
    
    # OCR-specific fields
    ocr_confidence: float = Field(..., description="Average OCR confidence (0-1)")
    extraction_confidence: float = Field(default=0.0, description="Clinical extraction confidence (0-1)")
    document_type: Optional[str] = Field(None, description="Detected document type")
    pages_with_data: List[int] = Field(default_factory=list, description="Page numbers containing extracted data")
    
    # Quality metrics
    text_quality_score: float = Field(default=0.0, description="Quality of OCR text (0-1)")
    extraction_notes: Optional[str] = Field(None, description="Notes about extraction quality/issues")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OCRBatch(BaseModel):
    """Batch upload and processing status."""
    batch_id: str = Field(..., description="Unique batch identifier")
    total_documents: int = Field(..., description="Total documents in batch")
    processed_documents: int = Field(default=0, description="Number processed so far")
    status: str = Field(default="pending", description="pending, processing, completed, failed")
    documents: List[Dict[str, Any]] = Field(default_factory=list, description="Document statuses")
    error_message: Optional[str] = Field(None, description="Error if batch failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# API Response Models

class OCRUploadResponse(BaseModel):
    """Response from document upload."""
    document_id: str = Field(..., description="Unique document ID")
    status: str = Field(...)
    filename: str = Field(...)
    total_pages: int = Field(...)
    overall_confidence: float = Field(...)
    message: Optional[str] = None


class OCRExtractionResponse(BaseModel):
    """Response from clinical extraction."""
    extraction_id: str = Field(...)
    document_id: str = Field(...)
    status: str = Field(...)
    clinical_extract: OCRClinicalExtract = Field(...)
    message: Optional[str] = None


class DocumentTypeDetectionResponse(BaseModel):
    """Response from document type detection."""
    document_id: str = Field(...)
    detected_type: str = Field(..., description="Type of document detected")
    confidence: float = Field(..., description="Confidence in type detection (0-1)")
    supported_extraction: bool = Field(..., description="Whether we can extract data from this type")
    message: Optional[str] = None

