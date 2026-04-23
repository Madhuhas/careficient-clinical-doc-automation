"""
FastAPI application for clinical audio processing pipeline.
Handles audio transcription via Whisper and structured data extraction.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import json
import tempfile
import subprocess
import uuid
from datetime import datetime
from typing import Optional

import numpy as np
import scipy.io.wavfile as _wavfile
import imageio_ffmpeg as _iio_ffmpeg

from fastapi import FastAPI, File, UploadFile, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import whisper
import torch

_FFMPEG_EXE = _iio_ffmpeg.get_ffmpeg_exe()


def _convert_to_wav(input_path: str, output_path: str) -> None:
    """Convert any audio file to 16kHz mono WAV using bundled ffmpeg."""
    subprocess.run(
        [_FFMPEG_EXE, '-y', '-i', input_path,
         '-ar', '16000', '-ac', '1', '-f', 'wav', output_path],
        check=True,
        capture_output=True,
    )


def _load_wav_as_float32(wav_path: str):
    """Load a WAV file and return (numpy float32 array, sample_rate)."""
    sr, data = _wavfile.read(wav_path)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    else:
        data = data.astype(np.float32)
    return data, sr

try:
    from .extractor import ClinicalExtractor
    from .models import (
        ClinicalExtract, OASISPrefill, TranscribeResponse, ExtractResponse,
        HealthCheckResponse, TranscribeRequest
    )
except ImportError:
    from audio_pipeline.extractor import ClinicalExtractor
    from audio_pipeline.models import (
        ClinicalExtract, OASISPrefill, TranscribeResponse, ExtractResponse,
        HealthCheckResponse, TranscribeRequest
    )


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="Careficient Audio Clinical Pipeline",
    version="1.0.0",
    description="Audio transcription and clinical data extraction API for healthcare providers",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global state
_model = None
_extractor = None

# In-memory storage for demo (use database in production)
_transcripts = {}
_extractions = {}


def get_whisper_model():
    """Lazy load Whisper model."""
    global _model
    if _model is None:
        logger.info("Loading Whisper model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        # Use 'base' model for better accuracy, 'tiny' for faster inference
        _model = whisper.load_model("base", device=device)
        logger.info("Whisper model loaded successfully")
    return _model


def get_extractor():
    """
    Return the configured extractor (regex / ollama / bedrock / anthropic).
    Provider is selected via EXTRACTOR_PROVIDER env var (default: regex).
    """
    global _extractor
    if _extractor is None:
        from audio_pipeline.extraction.factory import get_extractor as _factory
        _extractor = _factory()
        logger.info(f"Extractor provider: {_extractor.provider_name}")
    return _extractor


@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    logger.info("Starting up Careficient Audio Pipeline...")
    try:
        get_whisper_model()
        get_extractor()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    services = {
        "whisper_model": "loaded" if _model else "not loaded",
        "extractor": f"ready ({_extractor.provider_name})" if _extractor else "not ready",
    }
    return HealthCheckResponse(
        status="healthy",
        version="1.0.0",
        services=services
    )


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    patient_id: Optional[str] = None,
    visit_date: Optional[str] = None
):
    """
    Transcribe audio file using OpenAI Whisper.
    
    Args:
        audio: Audio file (mp3, wav, m4a, etc.)
        patient_id: Optional patient identifier
        visit_date: Optional visit date (YYYY-MM-DD)
    
    Returns:
        TranscribeResponse with transcript and metadata
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Audio file required")
    
    transcript_id = str(uuid.uuid4())
    input_path = None
    wav_path = None

    try:
        # Read audio data
        logger.info(f"Processing audio file: {audio.filename} (ID: {transcript_id})")
        audio_data = await audio.read()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Write uploaded bytes to a temp file
        suffix = Path(audio.filename).suffix or '.audio'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            input_path = f.name

        # Convert to 16kHz mono WAV using bundled ffmpeg (no system ffmpeg needed)
        logger.info("Converting audio to 16kHz mono WAV…")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name
        _convert_to_wav(input_path, wav_path)

        # Load WAV as float32 numpy array so Whisper skips its own ffmpeg call
        audio_array, sr = _load_wav_as_float32(wav_path)
        duration_seconds = len(audio_array) / sr

        # Transcribe using Whisper (numpy array path bypasses ffmpeg requirement)
        logger.info(f"Transcribing audio ({duration_seconds:.1f}s)…")
        model = get_whisper_model()
        result = model.transcribe(audio_array, language="en")
        
        transcript_text = result['text'].strip()
        language = result.get('language', 'en')
        
        logger.info(f"Transcription complete: {len(transcript_text)} chars, language: {language}")
        
        # Store transcript in memory
        _transcripts[transcript_id] = {
            'filename': audio.filename,
            'transcript': transcript_text,
            'duration_seconds': duration_seconds,
            'language': language,
            'patient_id': patient_id,
            'visit_date': visit_date,
            'created_at': datetime.utcnow().isoformat(),
            'confidence': result.get('confidence', None)
        }
        
        response = TranscribeResponse(
            transcript_id=transcript_id,
            status="success",
            transcript=transcript_text,
            duration_seconds=duration_seconds,
            language=language,
            message="Transcription completed successfully"
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
    
    finally:
        for p in (input_path, wav_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception as e:
                    logger.warning(f"Could not delete temp file {p}: {e}")


@app.post("/extract", response_model=ExtractResponse)
async def extract_clinical_data(transcript_id: str = Body(..., embed=True)):
    """
    Extract structured clinical data from a transcript.
    
    Args:
        transcript_id: ID of the transcript to extract from
    
    Returns:
        ExtractResponse with clinical data
    """
    if transcript_id not in _transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    extraction_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Extracting clinical data from transcript {transcript_id}")
        
        # Get stored transcript
        transcript_data = _transcripts[transcript_id]
        transcript_text = transcript_data['transcript']
        
        # Run extraction pipeline
        extractor = get_extractor()
        clinical_extract = extractor.extract_all(transcript_text)
        
        logger.info(
            f"Extraction complete: {len(clinical_extract.vitals)} vitals, "
            f"{len(clinical_extract.medications)} medications, "
            f"{len(clinical_extract.symptoms)} symptoms, "
            f"{len(clinical_extract.assessments)} assessments"
        )
        
        # Store extraction in memory
        _extractions[extraction_id] = {
            'transcript_id': transcript_id,
            'clinical_extract': clinical_extract.dict(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        response = ExtractResponse(
            extraction_id=extraction_id,
            transcript_id=transcript_id,
            status="success",
            clinical_extract=clinical_extract,
            confidence_score=clinical_extract.extraction_confidence,
            message="Clinical data extraction completed"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@app.get("/transcript/{transcript_id}")
async def get_transcript(transcript_id: str):
    """Retrieve a stored transcript."""
    if transcript_id not in _transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    return _transcripts[transcript_id]


@app.get("/extraction/{extraction_id}")
async def get_extraction(extraction_id: str):
    """Retrieve a stored extraction."""
    if extraction_id not in _extractions:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return _extractions[extraction_id]


@app.get("/transcripts")
async def list_transcripts():
    """List all transcripts."""
    return {
        "count": len(_transcripts),
        "transcripts": list(_transcripts.keys())
    }


@app.post("/oasis-prefill")
async def generate_oasis_prefill(
    transcript_id: str = Body(...),
    patient_id: str = Body(...),
    visit_date: str = Body(...)
):
    """
    Generate OASIS E1/E2 pre-fill JSON from extracted clinical data.
    
    Args:
        transcript_id: ID of transcript
        patient_id: Patient identifier
        visit_date: Visit date (YYYY-MM-DD)
    
    Returns:
        OASISPrefill JSON structure
    """
    if transcript_id not in _transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    # Get the extraction for this transcript
    extraction_for_transcript = None
    for ext_id, ext_data in _extractions.items():
        if ext_data['transcript_id'] == transcript_id:
            extraction_for_transcript = ext_data['clinical_extract']
            break
    
    if not extraction_for_transcript:
        raise HTTPException(status_code=400, detail="No extraction found for this transcript. Run extraction first.")
    
    # Create OASIS prefill
    clinical_extract = ClinicalExtract(**extraction_for_transcript)

    assessments = clinical_extract.assessments or []

    # M0210 — primary diagnosis with ICD code
    primary_dx = None
    if assessments:
        a = assessments[0]
        primary_dx = a.condition
        if a.icd_code:
            primary_dx += f" ({a.icd_code})"
        if a.severity:
            primary_dx += f" — {a.severity}"

    # M0230 — secondary diagnoses (all remaining)
    secondary_dx = None
    if len(assessments) > 1:
        parts = []
        for a in assessments[1:]:
            s = a.condition
            if a.icd_code:
                s += f" ({a.icd_code})"
            parts.append(s)
        secondary_dx = "; ".join(parts)

    # M0270 — health conditions summary (active medications)
    meds = clinical_extract.medications or []
    m0270_parts = []
    for m in meds:
        med_str = m.name
        if m.dosage:
            med_str += f" {m.dosage}"
        if m.frequency:
            med_str += f" {m.frequency}"
        m0270_parts.append(med_str)
    health_conditions = "; ".join(m0270_parts) if m0270_parts else None

    oasis_prefill = OASISPrefill(
        patient_id=patient_id,
        visit_date=visit_date,
        clinical_data=clinical_extract,
        oasis_m0100=clinical_extract.chief_complaint or "Not documented",
        oasis_m0200="; ".join([a.condition for a in assessments]) if assessments else "Not documented",
        oasis_m0210=primary_dx,
        oasis_m0230=secondary_dx,
        oasis_m0270=health_conditions,
        raw_audio_duration=_transcripts[transcript_id].get('duration_seconds')
    )
    
    logger.info(f"Generated OASIS prefill for patient {patient_id}")
    
    return oasis_prefill.dict()


@app.delete("/transcript/{transcript_id}")
async def delete_transcript(transcript_id: str):
    """Delete a transcript and associated extractions."""
    if transcript_id not in _transcripts:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    del _transcripts[transcript_id]
    
    # Also delete associated extractions
    extractions_to_delete = [
        ext_id for ext_id, ext_data in _extractions.items()
        if ext_data['transcript_id'] == transcript_id
    ]
    for ext_id in extractions_to_delete:
        del _extractions[ext_id]
    
    return {"message": f"Deleted transcript {transcript_id} and {len(extractions_to_delete)} extractions"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Careficient Audio Clinical Pipeline",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "transcribe": "POST /transcribe",
            "extract": "POST /extract",
            "oasis_prefill": "POST /oasis-prefill",
            "docs": "/api/docs",
            "redoc": "/api/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
if __name__ == '__main__':
    print("Run with: uvicorn app:app --reload")

