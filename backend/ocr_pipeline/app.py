"""
FastAPI application for OCR-based clinical document processing pipeline.
Handles PDF, image uploads, OCR, and clinical data extraction.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for module imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import uuid
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .extractor import OCRExtractor
    from .models import (
        OCRDocument, OCRClinicalExtract, OCRUploadResponse,
        OCRExtractionResponse, OCRBatch, DocumentTypeDetectionResponse
    )
except ImportError:
    from ocr_pipeline.extractor import OCRExtractor
    from ocr_pipeline.models import (
        OCRDocument, OCRClinicalExtract, OCRUploadResponse,
        OCRExtractionResponse, OCRBatch, DocumentTypeDetectionResponse
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(
    title="Careficient OCR Clinical Pipeline",
    version="1.0.0",
    description="OCR-based clinical data extraction from scanned documents and PDFs",
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
_extractor = None
_documents = {}  # In-memory storage (use database in production)
_extractions = {}


def get_ocr_extractor():
    """Lazy load OCR extractor."""
    global _extractor
    if _extractor is None:
        logger.info("Initializing OCR extractor...")
        _extractor = OCRExtractor()
        logger.info("OCR extractor ready")
    return _extractor


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting Careficient OCR Pipeline...")
    try:
        get_ocr_extractor()
        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "module": "ocr-pipeline",
        "version": "1.0.0",
        "extractor_ready": _extractor is not None
    }


@app.post("/ocr", response_model=OCRUploadResponse)
async def process_document(
    document: UploadFile = File(...),
    dpi: int = 300,
    patient_id: Optional[str] = None
):
    """
    Upload and process a document (PDF or image) with OCR.
    
    Args:
        document: PDF or image file
        dpi: DPI for OCR processing (default 300)
        patient_id: Optional patient identifier
    
    Returns:
        OCRUploadResponse with OCR results
    """
    if not document.filename:
        raise HTTPException(status_code=400, detail="Document filename required")
    
    # Validate file type
    allowed_types = {
        'application/pdf',
        'image/jpeg',
        'image/png',
        'image/tiff',
        'image/x-tiff'
    }
    
    if document.content_type not in allowed_types:
        logger.warning(f"Invalid document type: {document.content_type}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document format. Allowed: PDF, JPG, PNG, TIFF"
        )
    
    try:
        logger.info(f"Processing document: {document.filename}")
        
        # Read document
        document_data = await document.read()
        
        if len(document_data) == 0:
            raise HTTPException(status_code=400, detail="Empty document")
        
        # Process with OCR
        extractor = get_ocr_extractor()
        ocr_document = extractor.process_document(
            document_bytes=document_data,
            filename=document.filename,
            dpi=dpi
        )
        
        # Store in memory
        _documents[ocr_document.document_id] = {
            'document': ocr_document.dict(),
            'patient_id': patient_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        response = OCRUploadResponse(
            document_id=ocr_document.document_id,
            status="success",
            filename=ocr_document.filename,
            total_pages=ocr_document.total_pages,
            overall_confidence=ocr_document.overall_confidence,
            message=f"Successfully OCR'd {ocr_document.total_pages} page(s)"
        )
        
        logger.info(f"Document processed: {ocr_document.document_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )


@app.post("/extract", response_model=OCRExtractionResponse)
async def extract_clinical_data(document_id: str = Body(..., embed=True)):
    """
    Extract structured clinical data from OCR'd document.
    
    Args:
        document_id: ID of processed document
    
    Returns:
        OCRExtractionResponse with clinical data
    """
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    extraction_id = str(uuid.uuid4())
    
    try:
        logger.info(f"Extracting clinical data from document {document_id}")
        
        # Get stored document
        doc_data = _documents[document_id]['document']
        
        # Reconstruct OCRDocument for extraction
        ocr_doc_dict = doc_data
        ocr_document = OCRDocument(**ocr_doc_dict)
        
        # Run extraction
        extractor = get_ocr_extractor()
        clinical_extract = extractor.extract_clinical_data(ocr_document)
        
        logger.info(
            f"Extraction complete: {len(clinical_extract.vitals)} vitals, "
            f"{len(clinical_extract.medications)} meds, "
            f"{len(clinical_extract.symptoms)} symptoms, "
            f"{len(clinical_extract.assessments)} assessments"
        )
        
        # Store extraction
        _extractions[extraction_id] = {
            'document_id': document_id,
            'extraction': clinical_extract.dict(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        response = OCRExtractionResponse(
            extraction_id=extraction_id,
            document_id=document_id,
            status="success",
            clinical_extract=clinical_extract,
            message="Clinical data extraction completed"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Extraction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@app.get("/document-type/{document_id}", response_model=DocumentTypeDetectionResponse)
async def detect_document_type(document_id: str):
    """
    Detect the type of a processed document.
    
    Args:
        document_id: ID of processed document
    
    Returns:
        DocumentTypeDetectionResponse with detected type
    """
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        doc_data = _documents[document_id]['document']
        detected_type = doc_data.get('detected_document_type', 'Unknown')
        
        return DocumentTypeDetectionResponse(
            document_id=document_id,
            detected_type=detected_type,
            confidence=doc_data.get('overall_confidence', 0.5),
            supported_extraction=True,
            message=f"Document type detected: {detected_type}"
        )
    
    except Exception as e:
        logger.error(f"Type detection error: {e}")
        raise HTTPException(status_code=500, detail=f"Type detection failed: {str(e)}")


@app.get("/document/{document_id}")
async def get_document(document_id: str):
    """Retrieve a processed OCR document."""
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return _documents[document_id]


@app.get("/extraction/{extraction_id}")
async def get_extraction(extraction_id: str):
    """Retrieve an extraction result."""
    if extraction_id not in _extractions:
        raise HTTPException(status_code=404, detail="Extraction not found")
    
    return _extractions[extraction_id]


@app.get("/documents")
async def list_documents():
    """List all processed documents."""
    return {
        "count": len(_documents),
        "documents": [
            {
                "id": doc_id,
                "filename": doc_data['document'].get('filename'),
                "pages": doc_data['document'].get('total_pages'),
                "confidence": doc_data['document'].get('overall_confidence'),
                "type": doc_data['document'].get('detected_document_type')
            }
            for doc_id, doc_data in _documents.items()
        ]
    }


@app.post("/batch-upload")
async def batch_upload(
    documents: list = Body(...),
    patient_id: Optional[str] = None
):
    """
    Upload multiple documents for batch processing.
    
    Args:
        documents: List of files to process
        patient_id: Optional patient ID
    
    Returns:
        OCRBatch with processing status
    """
    batch_id = str(uuid.uuid4())
    
    batch_status = OCRBatch(
        batch_id=batch_id,
        total_documents=len(documents),
        status="pending",
        documents=[]
    )
    
    logger.info(f"Started batch processing: {batch_id} with {len(documents)} documents")
    
    return batch_status


@app.delete("/document/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and associated extractions."""
    if document_id not in _documents:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del _documents[document_id]
    
    # Delete associated extractions
    extractions_deleted = 0
    for ext_id, ext_data in list(_extractions.items()):
        if ext_data['document_id'] == document_id:
            del _extractions[ext_id]
            extractions_deleted += 1
    
    logger.info(f"Deleted document {document_id} and {extractions_deleted} extractions")
    
    return {
        "message": f"Deleted document {document_id}",
        "extractions_deleted": extractions_deleted
    }


@app.post("/compare-documents")
async def compare_documents(
    document_id_1: str = Body(...),
    document_id_2: str = Body(...)
):
    """
    Compare two OCR'd documents for consistency.
    Useful for verifying scanned vs. typed versions.
    """
    if document_id_1 not in _documents or document_id_2 not in _documents:
        raise HTTPException(status_code=404, detail="One or both documents not found")
    
    try:
        extractor = get_ocr_extractor()
        
        doc1_data = OCRDocument(**_documents[document_id_1]['document'])
        doc2_data = OCRDocument(**_documents[document_id_2]['document'])
        
        comparison = extractor.compare_documents(doc1_data, doc2_data)
        
        return {
            "document_1_id": document_id_1,
            "document_2_id": document_id_2,
            **comparison,
            "match_level": (
                "High" if comparison['similarity_score'] > 0.8
                else "Medium" if comparison['similarity_score'] > 0.5
                else "Low"
            )
        }
    
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Careficient OCR Clinical Pipeline",
        "version": "1.0.0",
        "description": "OCR-based clinical data extraction from scanned documents",
        "endpoints": {
            "health": "/health",
            "upload_document": "POST /ocr",
            "extract_clinical_data": "POST /extract",
            "detect_document_type": "GET /document-type/{document_id}",
            "list_documents": "GET /documents",
            "compare_documents": "POST /compare-documents",
            "docs": "/api/docs",
            "redoc": "/api/redoc"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)

