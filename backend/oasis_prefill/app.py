"""
OASIS Prefill FastAPI server.
Exposes OASIS form generation via REST API.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid

from .mapper import OASISMapper
from .models import OASISPrefillResponse, OASISBatchRequest, OASISBatchResponse
from .config import CONFIG, DEFAULT_FORM_VERSION

# Handle imports for common module
try:
    from ..common.logging_config import setup_logging, log_with_data
    from ..common.errors import CareficentException, handle_exception, ErrorCode
    from ..common.utils import generate_id
except ImportError:
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from common.logging_config import setup_logging, log_with_data
    from common.errors import CareficentException, handle_exception, ErrorCode
    from common.utils import generate_id

# Setup logging
setup_logging(__name__, log_file=CONFIG["log_file"], level=CONFIG["log_level"])
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="OASIS Prefill API",
    description="Generate pre-filled OASIS assessment forms from clinical extractions",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
prefills = {}  # prefill_id -> OASISPrefillResponse
batch_jobs = {}  # batch_id -> OASISBatchResponse


# ============================================================================
# Utility Functions
# ============================================================================

def get_extraction_from_pipelines(extraction_id: str):
    """
    Retrieve extraction from audio or OCR pipeline.
    
    Args:
        extraction_id: Extraction ID (EXT_xxx format)
    
    Returns:
        Clinical extraction
    
    Raises:
        HTTPException if not found
    """
    try:
        # Try audio pipeline first
        try:
            from ..audio_pipeline.app import extractions as audio_extractions
        except ImportError:
            from audio_pipeline.app import extractions as audio_extractions
        
        if extraction_id in audio_extractions:
            return ("audio", audio_extractions[extraction_id])
        
        # Try OCR pipeline
        try:
            from ..ocr_pipeline.app import extractions as ocr_extractions
        except ImportError:
            from ocr_pipeline.app import extractions as ocr_extractions
        
        if extraction_id in ocr_extractions:
            return ("ocr", ocr_extractions[extraction_id])
        
        # Not found
        raise HTTPException(
            status_code=404,
            detail=f"Extraction not found: {extraction_id}"
        )
    except Exception as e:
        logger.error(f"Error retrieving extraction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "service": "OASIS Prefill API",
        "version": "1.0.0",
        "endpoints": {
            "prefill": "POST /prefill - Generate OASIS form",
            "get_prefill": "GET /prefill/{prefill_id} - Retrieve prefill",
            "list_prefills": "GET /prefills - List all prefills",
            "delete_prefill": "DELETE /prefill/{prefill_id} - Delete prefill",
            "batch_prefill": "POST /batch-prefill - Batch process extractions",
            "batch_status": "GET /batch/{batch_id} - Get batch status",
            "health": "GET /health - Health check",
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "OASIS Prefill",
        "timestamp": datetime.now().isoformat(),
        "prefills_stored": len(prefills),
        "batch_jobs": len(batch_jobs),
    }


@app.post("/prefill", response_model=OASISPrefillResponse)
async def generate_prefill(
    extraction_id: str,
    patient_id: str,
    form_version: str = DEFAULT_FORM_VERSION,
    clinician_name: str = None,
):
    """
    Generate OASIS form from clinical extraction.
    
    Args:
        extraction_id: ID from audio or OCR pipeline
        patient_id: Patient identifier
        form_version: "E1" or "E2" (default: E1)
        clinician_name: Optional clinician name
    
    Returns:
        OASISPrefillResponse with generated form
    
    Raises:
        HTTPException on error
    """
    try:
        # Validate form version
        if form_version not in ["E1", "E2"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid form_version: {form_version}. Must be 'E1' or 'E2'"
            )
        
        # Get extraction from pipelines
        source, extraction = get_extraction_from_pipelines(extraction_id)
        
        # Initialize mapper
        mapper = OASISMapper(form_version=form_version)
        
        # Generate prefill based on source
        if source == "audio":
            response = mapper.map_audio_extraction(
                extraction,
                patient_id=patient_id,
                clinician_name=clinician_name,
            )
        else:  # ocr
            response = mapper.map_ocr_extraction(
                extraction,
                patient_id=patient_id,
                clinician_name=clinician_name,
            )
        
        # Store prefill
        prefill_id = generate_id("PREFILL")
        prefills[prefill_id] = response
        
        # Log
        log_with_data(
            logger,
            "info",
            "OASIS form generated",
            {
                "prefill_id": prefill_id,
                "extraction_id": extraction_id,
                "patient_id": patient_id,
                "form_version": form_version,
                "source": source,
                "confidence": response.confidence_score,
                "status": response.validation_status,
                "fields_filled": len(response.auto_filled_fields),
            }
        )
        
        # Return response with prefill_id in extras
        response_dict = response.model_dump()
        response_dict["prefill_id"] = prefill_id
        
        return JSONResponse(content=response_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating prefill: {e}")
        error_response = handle_exception(e)
        raise HTTPException(status_code=500, detail=error_response)


@app.get("/prefill/{prefill_id}")
async def get_prefill(prefill_id: str):
    """
    Retrieve stored OASIS prefill.
    
    Args:
        prefill_id: Prefill identifier
    
    Returns:
        OASISPrefillResponse
    
    Raises:
        HTTPException if not found
    """
    if prefill_id not in prefills:
        raise HTTPException(
            status_code=404,
            detail=f"Prefill not found: {prefill_id}"
        )
    
    response = prefills[prefill_id]
    response_dict = response.model_dump()
    response_dict["prefill_id"] = prefill_id
    
    return response_dict


@app.get("/prefills")
async def list_prefills(skip: int = 0, limit: int = 100):
    """
    List all stored OASIS prefills.
    
    Args:
        skip: Number of results to skip
        limit: Maximum results to return
    
    Returns:
        List of prefill metadata
    """
    items = []
    for prefill_id, response in list(prefills.items())[skip:skip+limit]:
        items.append({
            "prefill_id": prefill_id,
            "extraction_id": response.extraction_id,
            "patient_id": response.patient_id,
            "form_version": response.form_version,
            "confidence": response.confidence_score,
            "status": response.validation_status,
            "generated_at": response.generated_at.isoformat(),
        })
    
    return {
        "total": len(prefills),
        "skip": skip,
        "limit": limit,
        "items": items,
    }


@app.delete("/prefill/{prefill_id}")
async def delete_prefill(prefill_id: str):
    """
    Delete stored OASIS prefill.
    
    Args:
        prefill_id: Prefill identifier
    
    Returns:
        Confirmation
    
    Raises:
        HTTPException if not found
    """
    if prefill_id not in prefills:
        raise HTTPException(
            status_code=404,
            detail=f"Prefill not found: {prefill_id}"
        )
    
    del prefills[prefill_id]
    
    logger.info(f"Deleted prefill: {prefill_id}")
    
    return {
        "status": "deleted",
        "prefill_id": prefill_id,
    }


@app.post("/batch-prefill")
async def batch_prefill(request: OASISBatchRequest):
    """
    Batch process multiple extractions into OASIS forms.
    
    Args:
        request: OASISBatchRequest with extraction_ids, form_version, etc.
    
    Returns:
        OASISBatchResponse with results
    
    Raises:
        HTTPException on error
    """
    try:
        batch_id = generate_id("BATCH")
        
        results = []
        errors = []
        successful = 0
        failed = 0
        
        for extraction_id in request.extraction_ids:
            try:
                # Get extraction
                source, extraction = get_extraction_from_pipelines(extraction_id)
                
                # Generate prefill
                mapper = OASISMapper(form_version=request.form_version)
                
                if source == "audio":
                    response = mapper.map_audio_extraction(
                        extraction,
                        patient_id=extraction_id.replace("EXT_", "P_"),  # Simple mapping
                    )
                else:
                    response = mapper.map_ocr_extraction(
                        extraction,
                        patient_id=extraction_id.replace("EXT_", "P_"),
                    )
                
                # Store result
                prefill_id = generate_id("PREFILL")
                prefills[prefill_id] = response
                
                results.append({
                    "extraction_id": extraction_id,
                    "prefill_id": prefill_id,
                    "status": "success",
                    "confidence": response.confidence_score,
                    "validation_status": response.validation_status,
                })
                successful += 1
            
            except Exception as e:
                failed += 1
                errors.append({
                    "extraction_id": extraction_id,
                    "error": str(e),
                })
        
        # Create batch response
        batch_response = OASISBatchResponse(
            batch_id=batch_id,
            counts={
                "total": len(request.extraction_ids),
                "successful": successful,
                "failed": failed,
            },
            results=results,
            errors=errors,
            timestamps={
                "created_at": datetime.now(),
                "completed_at": datetime.now(),
            },
        )
        
        # Store batch job
        batch_jobs[batch_id] = batch_response
        
        # Log
        log_with_data(
            logger,
            "info",
            "Batch prefill completed",
            {
                "batch_id": batch_id,
                "total": len(request.extraction_ids),
                "successful": successful,
                "failed": failed,
            }
        )
        
        return batch_response.model_dump()
    
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """
    Get batch processing status.
    
    Args:
        batch_id: Batch identifier
    
    Returns:
        Batch status and results
    
    Raises:
        HTTPException if not found
    """
    if batch_id not in batch_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Batch job not found: {batch_id}"
        )
    
    batch = batch_jobs[batch_id]
    
    return batch.model_dump()


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(CareficentException)
async def careficient_exception_handler(request, exc):
    """Handle CareficentException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code.value,
            "message": str(exc),
            "details": exc.details,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info("OASIS Prefill API starting up...")
    logger.info(f"Configuration: {CONFIG}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("OASIS Prefill API shutting down...")
    logger.info(f"Stored {len(prefills)} prefills and {len(batch_jobs)} batch jobs")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=CONFIG["api_host"],
        port=CONFIG["api_port"],
        log_level=CONFIG["log_level"].lower(),
    )
