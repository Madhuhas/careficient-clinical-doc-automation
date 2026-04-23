"""
Unit tests for OCR pipeline module.
"""

import pytest
from extractor import OCRExtractor
from models import OCRPage, OCRDocument, OCRClinicalExtract


class TestOCRExtractor:
    """Tests for OCR Extractor."""
    
    @pytest.fixture
    def extractor(self):
        return OCRExtractor()
    
    def test_document_type_detection_vitals(self, extractor):
        """Test detection of vital signs sheet."""
        text = "Patient vitals: BP 140/90, HR 78 bpm, Temperature 98.6"
        doc_type = extractor._detect_document_type(text)
        assert "vital" in doc_type.lower()
    
    def test_document_type_detection_medication(self, extractor):
        """Test detection of medication list."""
        text = "Current Medications: Lisinopril 10mg daily, Metformin 500mg BID"
        doc_type = extractor._detect_document_type(text)
        assert "medication" in doc_type.lower()
    
    def test_document_type_detection_assessment(self, extractor):
        """Test detection of assessment form."""
        text = "ASSESSMENT: Patient with hypertension and diabetes"
        doc_type = extractor._detect_document_type(text)
        assert "assessment" in doc_type.lower() or "note" in doc_type.lower()
    
    def test_text_quality_calculation(self, extractor):
        """Test text quality score calculation."""
        # Good quality text
        good_text = "Patient presents with chest pain. BP 120/80, HR 72 bpm"
        good_score = extractor._calculate_text_quality(good_text)
        assert 0 <= good_score <= 1
        
        # Poor quality text (short)
        poor_text = "abc"
        poor_score = extractor._calculate_text_quality(poor_text)
        assert poor_score < good_score
    
    def test_table_detection(self, extractor):
        """Test table detection in OCR text."""
        text_with_table = """
        Date | BP | HR | Temp
        2024-01-01 | 120/80 | 72 | 98.6
        2024-01-02 | 122/82 | 74 | 98.7
        """
        tables = extractor._detect_tables(text_with_table)
        assert len(tables) > 0
    
    def test_form_field_detection(self, extractor):
        """Test form field detection."""
        text_with_form = """
        Patient Name: John Doe
        Date of Birth: 01/01/1990
        Blood Pressure: 120/80
        """
        forms = extractor._detect_forms(text_with_form)
        assert len(forms) > 0
        assert any("name" in f['field_name'].lower() for f in forms)


class TestOCRModels:
    """Tests for OCR data models."""
    
    def test_ocr_page_model(self):
        """Test OCRPage model."""
        page = OCRPage(
            page_number=1,
            raw_text="Test page text",
            confidence=0.85,
            text_blocks=["Block 1", "Block 2"]
        )
        assert page.page_number == 1
        assert page.confidence == 0.85
        assert len(page.text_blocks) == 2
    
    def test_ocr_document_model(self):
        """Test OCRDocument model."""
        pages = [
            OCRPage(page_number=1, raw_text="Page 1", confidence=0.8),
            OCRPage(page_number=2, raw_text="Page 2", confidence=0.85)
        ]
        doc = OCRDocument(
            document_id="doc123",
            filename="test.pdf",
            file_type="pdf",
            pages=pages,
            total_pages=2,
            raw_full_text="Page 1\nPage 2",
            overall_confidence=0.825
        )
        assert doc.total_pages == 2
        assert doc.overall_confidence == 0.825
    
    def test_ocr_clinical_extract_model(self):
        """Test OCRClinicalExtract model."""
        extract = OCRClinicalExtract(
            extraction_id="ext123",
            document_id="doc123",
            vitals=[],
            medications=[],
            symptoms=[],
            assessments=[],
            raw_transcript="test text",
            ocr_confidence=0.85
        )
        assert extract.extraction_id == "ext123"
        assert extract.ocr_confidence == 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
