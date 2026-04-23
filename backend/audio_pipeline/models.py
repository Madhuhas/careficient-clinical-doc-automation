"""
Pydantic models for audio pipeline data validation and serialization.
Supports clinical data extraction from transcripts and OASIS pre-filling.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import json


class VitalSign(BaseModel):
    """Represents a single vital sign measurement."""
    name: str = Field(..., description="Vital sign name (BP, HR, RR, TEMP, SPO2)")
    value: str = Field(..., description="Measured value")
    unit: Optional[str] = Field(None, description="Unit of measurement (mmHg, bpm, %, etc.)")
    reference_range: Optional[str] = Field(None, description="Normal reference range")
    timestamp: Optional[str] = Field(None, description="Time measurement was taken")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Blood Pressure",
                "value": "120/80",
                "unit": "mmHg",
                "reference_range": "< 120/80"
            }
        }


class Medication(BaseModel):
    """Represents a medication mentioned in clinical encounter."""
    name: str = Field(..., description="Medication name")
    dosage: Optional[str] = Field(None, description="Dosage (e.g., '500mg', 'two tablets')")
    frequency: Optional[str] = Field(None, description="Frequency (daily, bid, tid, q4h, etc.)")
    route: Optional[str] = Field(None, description="Route (oral, IV, IM, topical, etc.)")
    status: Optional[str] = Field(None, description="Status (active, discontinued, new, changed)")
    indication: Optional[str] = Field(None, description="Reason for medication")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily",
                "route": "oral",
                "status": "active"
            }
        }


class Symptom(BaseModel):
    """Represents a reported symptom."""
    name: str = Field(..., description="Symptom name")
    severity: Optional[str] = Field(None, description="Severity (mild, moderate, severe or 1-10)")
    duration: Optional[str] = Field(None, description="Duration (e.g., '3 days', 'since yesterday')")
    location: Optional[str] = Field(None, description="Body location")
    description: Optional[str] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "chest pain",
                "severity": "moderate",
                "duration": "2 days",
                "location": "central chest"
            }
        }


class Assessment(BaseModel):
    """Represents clinical assessment or diagnosis."""
    condition: str = Field(..., description="Condition or diagnosis")
    icd_code: Optional[str] = Field(None, description="ICD-10 code if identified")
    notes: Optional[str] = Field(None, description="Additional clinical notes")
    severity: Optional[str] = Field(None, description="Severity (mild, moderate, severe)")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")

    class Config:
        json_schema_extra = {
            "example": {
                "condition": "Hypertension",
                "icd_code": "I10",
                "severity": "moderate"
            }
        }


class ClinicalExtract(BaseModel):
    """Structured clinical data extracted from transcript."""
    vitals: List[VitalSign] = Field(default_factory=list)
    medications: List[Medication] = Field(default_factory=list)
    symptoms: List[Symptom] = Field(default_factory=list)
    assessments: List[Assessment] = Field(default_factory=list)
    chief_complaint: Optional[str] = Field(None, description="Chief complaint or reason for visit")
    clinical_notes: Optional[str] = Field(None, description="General clinical notes")
    plan: Optional[str] = Field(None, description="Clinical plan or recommendations")
    raw_transcript: str = Field(..., description="Raw Whisper transcript")
    extraction_confidence: float = Field(default=0.0, description="Overall extraction confidence (0-1)")


class OASISPrefill(BaseModel):
    """OASIS E1/E2 pre-fill template with clinical data."""
    patient_id: str = Field(..., description="Patient identifier")
    visit_date: str = Field(..., description="Visit date (YYYY-MM-DD)")
    clinical_data: ClinicalExtract = Field(..., description="Extracted clinical data")
    
    # OASIS fields (subset for MVP)
    oasis_m0100: Optional[str] = Field(None, description="OASIS E1 M0100 - Reason for Referral")
    oasis_m0200: Optional[str] = Field(None, description="OASIS E2 M0200 - Conditions Being Treated")
    oasis_m0210: Optional[str] = Field(None, description="OASIS M0210 - Primary Diagnosis")
    oasis_m0230: Optional[str] = Field(None, description="OASIS M0230 - Secondary Diagnoses")
    oasis_m0270: Optional[str] = Field(None, description="OASIS M0270 - Health Conditions")
    
    raw_audio_duration: Optional[float] = Field(None, description="Audio duration in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# API Request/Response Models

class TranscribeRequest(BaseModel):
    """Request model for transcription."""
    patient_id: Optional[str] = Field(None, description="Patient ID")
    visit_date: Optional[str] = Field(None, description="Visit date")
    visit_type: Optional[str] = Field(None, description="Type of visit")


class TranscribeResponse(BaseModel):
    """Response model for transcription results."""
    transcript_id: str = Field(..., description="Unique transcript ID")
    status: str = Field(..., description="Processing status (success/error)")
    transcript: str = Field(..., description="Full transcribed text")
    duration_seconds: float = Field(..., description="Audio duration")
    language: str = Field(..., description="Detected language")
    message: Optional[str] = Field(None, description="Status message")


class ExtractResponse(BaseModel):
    """Response model for extraction results."""
    extraction_id: str = Field(..., description="Unique extraction ID")
    transcript_id: str = Field(..., description="Source transcript ID")
    status: str = Field(..., description="Processing status")
    clinical_extract: ClinicalExtract = Field(..., description="Extracted data")
    confidence_score: float = Field(..., description="Overall confidence (0-1)")
    message: Optional[str] = Field(None)


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    services: Dict[str, str] = Field(default_factory=dict, description="Status of dependent services")


def transcript_to_json(transcript: str) -> Dict[str, Any]:
    """Utility to convert transcript string to JSON dict."""
    return json.loads(json.dumps({
        'transcript': transcript,
        'extracted': ClinicalExtract(raw_transcript=transcript).dict()
    }))

