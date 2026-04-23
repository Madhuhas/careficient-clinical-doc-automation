"""
OCR-based clinical data extraction from documents.
Handles PDF, images, and scanned documents using Tesseract OCR.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple
import re
from datetime import datetime

try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_bytes
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logging.warning("Tesseract or PIL not available. Using fallback OCR.")

try:
    from audio_pipeline.extractor import ClinicalExtractor
    from audio_pipeline.models import VitalSign, Medication, Symptom, Assessment
except ImportError:
    # Fallback for standalone testing
    from .models import VitalSign, Medication, Symptom, Assessment
    ClinicalExtractor = None

from .models import OCRDocument, OCRPage, OCRClinicalExtract


logger = logging.getLogger(__name__)


class OCRExtractor:
    """Extract clinical data from scanned documents using OCR."""
    
    # Document type keywords
    DOCUMENT_TYPE_PATTERNS = {
        'vital_signs_sheet': r'vital|bp|blood pressure|heart rate|temperature|respiration',
        'medication_list': r'medication|drug|pharmacy|rx|prescription|prescribe',
        'assessment_form': r'assessment|diagnosis|note|impression|evaluation',
        'lab_results': r'lab|laboratory|result|test|panel|value|normal|abnormal',
        'discharge_summary': r'discharge|summary|hospital|admission|treated',
        'progress_note': r'progress|note|visit|encounter|follow.?up',
        'physical_exam': r'physical exam|pe|examination|palpat|auscultat|percussion'
    }
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize OCR extractor.
        
        Args:
            tesseract_path: Path to tesseract executable (Windows/Linux)
        """
        self.tesseract_available = TESSERACT_AVAILABLE
        self.clinical_extractor = ClinicalExtractor() if ClinicalExtractor else None
        
        if tesseract_path and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        logger.info(f"OCRExtractor initialized (Tesseract available: {self.tesseract_available})")
    
    def process_document(
        self,
        document_bytes: bytes,
        filename: str,
        file_type: Optional[str] = None,
        dpi: int = 300
    ) -> OCRDocument:
        """
        Process a document (PDF or image) and extract text using OCR.
        
        Args:
            document_bytes: Raw document bytes
            filename: Original filename
            file_type: File type (pdf, jpg, png, etc.)
            dpi: DPI for OCR processing
        
        Returns:
            OCRDocument with OCR results
        """
        if not file_type:
            file_type = filename.split('.')[-1].lower()
        
        document_id = str(uuid.uuid4())
        logger.info(f"Processing document: {filename} (ID: {document_id})")
        
        start_time = datetime.utcnow()
        pages = []
        
        try:
            # Convert document to images
            if file_type.lower() in ['pdf', 'PDF']:
                images = convert_from_bytes(document_bytes, dpi=dpi)
            else:
                # Treat as image
                from PIL import Image
                import io
                images = [Image.open(io.BytesIO(document_bytes))]
            
            logger.info(f"Document has {len(images)} page(s)")
            
            # OCR each page
            all_text = []
            confidences = []
            
            for page_num, image in enumerate(images, 1):
                page_data = self._ocr_page(image, page_num, dpi)
                pages.append(page_data)
                all_text.append(page_data.raw_text)
                confidences.append(page_data.confidence)
            
            # Calculate statistics
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            full_text = "\n\n".join(all_text)
            
            # Detect document type
            doc_type = self._detect_document_type(full_text)
            
            ocr_document = OCRDocument(
                document_id=document_id,
                filename=filename,
                file_type=file_type,
                pages=pages,
                total_pages=len(pages),
                raw_full_text=full_text,
                overall_confidence=overall_confidence,
                detected_document_type=doc_type,
                processing_time_seconds=processing_time
            )
            
            logger.info(
                f"OCR complete: {len(pages)} pages, "
                f"confidence: {overall_confidence:.2f}, "
                f"type: {doc_type}, "
                f"time: {processing_time:.2f}s"
            )
            
            return ocr_document
        
        except Exception as e:
            logger.error(f"Document processing error: {e}", exc_info=True)
            raise
    
    def _ocr_page(self, image: 'Image.Image', page_num: int, dpi: int = 300) -> OCRPage:
        """
        OCR a single page/image.
        
        Args:
            image: PIL Image object
            page_num: Page number
            dpi: DPI for OCR
        
        Returns:
            OCRPage with OCR results
        """
        try:
            if not self.tesseract_available:
                logger.warning("Tesseract not available, using fallback")
                return OCRPage(
                    page_number=page_num,
                    raw_text="[Tesseract not available]",
                    confidence=0.0,
                    text_blocks=[],
                    detected_tables=[],
                    detected_forms=[]
                )
            
            # Optimize image for OCR
            image = self._preprocess_image(image)
            
            # Run OCR
            config = '--psm 1 --oem 3 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,/-(): '
            raw_text = pytesseract.image_to_string(image, config=config)
            
            # Get confidence
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(c) for c in data['confidence'] if c != '-1']
            confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.5
            
            # Detect text blocks
            text_blocks = raw_text.split('\n\n') if raw_text else []
            
            # Detect tables (basic pattern matching)
            detected_tables = self._detect_tables(raw_text)
            
            # Detect forms
            detected_forms = self._detect_forms(raw_text)
            
            page = OCRPage(
                page_number=page_num,
                raw_text=raw_text.strip(),
                confidence=confidence,
                text_blocks=text_blocks,
                detected_tables=detected_tables,
                detected_forms=detected_forms
            )
            
            logger.debug(f"Page {page_num}: {len(raw_text)} chars, confidence: {confidence:.2f}")
            return page
        
        except Exception as e:
            logger.error(f"Page {page_num} OCR error: {e}")
            return OCRPage(
                page_number=page_num,
                raw_text=f"Error processing page: {str(e)}",
                confidence=0.0
            )
    
    def _preprocess_image(self, image: 'Image.Image') -> 'Image.Image':
        """Preprocess image for better OCR."""
        try:
            from PIL import ImageEnhance, ImageFilter
            
            # Convert to grayscale
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Enhance brightness
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(1.1)
            
            # Apply sharpening filter
            image = image.filter(ImageFilter.SHARPEN)
            
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}")
            return image
    
    def _detect_tables(self, text: str) -> List[Dict[str, Any]]:
        """Detect tables in OCR'd text."""
        tables = []
        
        # Simple heuristic: detect lines with many pipes or multiple aligned values
        lines = text.split('\n')
        
        current_table_lines = []
        for line in lines:
            # Check if line looks like a table row
            if '|' in line or (len(line.split()) > 3 and line.count(' ') > 5):
                current_table_lines.append(line)
            elif current_table_lines and len(current_table_lines) > 2:
                tables.append({
                    'type': 'tabular',
                    'rows': current_table_lines,
                    'row_count': len(current_table_lines)
                })
                current_table_lines = []
        
        return tables
    
    def _detect_forms(self, text: str) -> List[Dict[str, str]]:
        """Detect form fields in OCR'd text."""
        forms = []
        
        # Look for patterns like "Field: value" or "Field: _____"
        pattern = r'([A-Za-z\s]+)[:\s]+([A-Za-z0-9\s\-/]*)'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            field_name = match.group(1).strip()
            field_value = match.group(2).strip()
            
            if len(field_name) > 2 and len(field_name) < 50:
                forms.append({
                    'field_name': field_name,
                    'field_value': field_value
                })
        
        return forms[:10]  # Limit to first 10 forms
    
    def _detect_document_type(self, text: str) -> str:
        """Detect document type from text content."""
        text_lower = text.lower()
        scores = {}
        
        for doc_type, pattern in self.DOCUMENT_TYPE_PATTERNS.items():
            matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
            if matches > 0:
                scores[doc_type] = matches
        
        if scores:
            detected_type = max(scores, key=scores.get)
            return detected_type.replace('_', ' ').title()
        
        return "Unknown Document"
    
    def extract_clinical_data(self, ocr_document: OCRDocument) -> OCRClinicalExtract:
        """
        Extract structured clinical data from OCR'd document.
        
        Args:
            ocr_document: OCR'd document with text
        
        Returns:
            OCRClinicalExtract with structured clinical data
        """
        extraction_id = str(uuid.uuid4())
        
        try:
            logger.info(f"Extracting clinical data from document {ocr_document.document_id}")
            
            # Extract using clinical extractor (reuses audio pipeline logic)
            if self.clinical_extractor:
                clinical_data = self.clinical_extractor.extract_all(ocr_document.raw_full_text)
                
                # Convert to OCR extraction model
                extract = OCRClinicalExtract(
                    extraction_id=extraction_id,
                    document_id=ocr_document.document_id,
                    vitals=clinical_data.vitals,
                    medications=clinical_data.medications,
                    symptoms=clinical_data.symptoms,
                    assessments=clinical_data.assessments,
                    raw_transcript=ocr_document.raw_full_text,
                    ocr_confidence=ocr_document.overall_confidence,
                    extraction_confidence=clinical_data.extraction_confidence,
                    document_type=ocr_document.detected_document_type,
                    text_quality_score=self._calculate_text_quality(ocr_document.raw_full_text),
                    chief_complaint=clinical_data.chief_complaint,
                    plan=clinical_data.plan
                )
            else:
                # Fallback extraction
                logger.warning("Clinical extractor not available, using basic extraction")
                extract = OCRClinicalExtract(
                    extraction_id=extraction_id,
                    document_id=ocr_document.document_id,
                    vitals=[],
                    medications=[],
                    symptoms=[],
                    assessments=[],
                    raw_transcript=ocr_document.raw_full_text,
                    ocr_confidence=ocr_document.overall_confidence,
                    extraction_confidence=0.0,
                    document_type=ocr_document.detected_document_type
                )
            
            logger.info(
                f"Extraction complete: {len(extract.vitals)} vitals, "
                f"{len(extract.medications)} meds, "
                f"{len(extract.symptoms)} symptoms"
            )
            
            return extract
        
        except Exception as e:
            logger.error(f"Clinical extraction error: {e}", exc_info=True)
            raise
    
    def _calculate_text_quality(self, text: str) -> float:
        """Calculate quality score of OCR'd text."""
        if not text:
            return 0.0
        
        # Heuristics for text quality
        score = 1.0
        
        # Penalize for short text
        if len(text) < 100:
            score *= 0.5
        elif len(text) < 500:
            score *= 0.7
        
        # Penalize for many unrecognized characters
        unrecognized = len(re.findall(r'[^A-Za-z0-9\s\n\.,\-\(\)/:]', text))
        if unrecognized > len(text) * 0.1:
            score *= 0.8
        
        # Bonus for clinical keywords
        clinical_keywords = ['bp', 'hr', 'medication', 'diagnosis', 'treatment', 'patient', 'visit']
        found_keywords = sum(1 for kw in clinical_keywords if kw in text.lower())
        score *= (1.0 + found_keywords * 0.05)
        
        return min(score, 1.0)
    
    def compare_documents(
        self,
        doc1: OCRDocument,
        doc2: OCRDocument
    ) -> Dict[str, Any]:
        """
        Compare two OCR'd documents for consistency.
        Useful for verifying scanned vs. typed versions.
        """
        from difflib import SequenceMatcher
        
        similarity = SequenceMatcher(
            None,
            doc1.raw_full_text.lower(),
            doc2.raw_full_text.lower()
        ).ratio()
        
        return {
            'similarity_score': similarity,
            'doc1_confidence': doc1.overall_confidence,
            'doc2_confidence': doc2.overall_confidence,
            'average_confidence': (doc1.overall_confidence + doc2.overall_confidence) / 2,
            'doc1_pages': doc1.total_pages,
            'doc2_pages': doc2.total_pages
        }

