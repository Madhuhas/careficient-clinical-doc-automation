"""
Unit tests for OASIS Prefill module.
Tests mapper logic, field extraction, validation, and confidence scoring.
"""

import pytest
from datetime import datetime, date
from audio_pipeline.models import (
    ClinicalExtract,
    VitalSign,
    Medication,
    Symptom,
    Assessment,
)
from ocr_pipeline.models import OCRClinicalExtract
from oasis_prefill.mapper import OASISMapper
from oasis_prefill.models import OASISPrefillResponse


class TestOASISMapper:
    """Test OASIS mapper functionality."""
    
    @pytest.fixture
    def mapper_e1(self):
        """Create E1 mapper."""
        return OASISMapper(form_version="E1")
    
    @pytest.fixture
    def mapper_e2(self):
        """Create E2 mapper."""
        return OASISMapper(form_version="E2")
    
    @pytest.fixture
    def sample_extraction(self):
        """Create sample clinical extraction."""
        return ClinicalExtract(
            extraction_id="EXT_test123",
            vitals=[
                VitalSign(name="blood pressure", value="140/90", unit="mmHg"),
                VitalSign(name="heart rate", value="78 bpm", unit="bpm"),
                VitalSign(name="temperature", value="98.6", unit="F"),
                VitalSign(name="respiratory rate", value="16", unit="breaths/min"),
                VitalSign(name="weight", value="165 lbs", unit="lbs"),
                VitalSign(name="height", value="70 inches", unit="in"),
            ],
            medications=[
                Medication(name="Lisinopril", dose="10mg", frequency="daily", route="oral"),
                Medication(name="Metformin", dose="500mg", frequency="twice daily", route="oral"),
            ],
            symptoms=[
                Symptom(name="pain", severity=7),
                Symptom(name="anxiety", severity=4),
                Symptom(name="ambulation difficulty", severity=2),
            ],
            assessments=[
                Assessment(name="Type 2 Diabetes", icd10_code="E11.9"),
                Assessment(name="Hypertension", icd10_code="I10"),
            ],
            chief_complaint="Routine follow-up for diabetes management",
            plan="Continue current medications, monitor blood sugar",
            confidence=0.85,
        )
    
    def test_map_audio_extraction_e1(self, mapper_e1, sample_extraction):
        """Test mapping audio extraction to E1 form."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001",
            clinician_name="Dr. Smith"
        )
        
        assert isinstance(response, OASISPrefillResponse)
        assert response.extraction_id == "EXT_test123"
        assert response.patient_id == "P001"
        assert response.form_version == "E1"
        assert response.form_data is not None
        assert len(response.form_data) > 0
    
    def test_map_vital_signs(self, mapper_e1, sample_extraction):
        """Test vital signs extraction and mapping."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        vitals = response.form_data.get("vital_signs", {})
        
        # Check vital signs were parsed
        assert vitals.get("blood_pressure_systolic") == 140
        assert vitals.get("blood_pressure_diastolic") == 90
        assert vitals.get("pulse_rate") == 78
        assert vitals.get("temperature") == 98.6
        assert vitals.get("respiratory_rate") == 16
        assert vitals.get("weight") == 165
        assert vitals.get("height") == 70
    
    def test_map_medications(self, mapper_e1, sample_extraction):
        """Test medication extraction and mapping."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        meds = response.form_data.get("medications", {})
        
        # Check medications
        assert meds.get("number_of_medications") == 2
        assert len(meds.get("medications", [])) == 2
        
        # Check first medication
        med = meds["medications"][0]
        assert med["name"] == "Lisinopril"
        assert med["dose"] == "10mg"
        assert med["frequency"] == "daily"
    
    def test_map_assessments(self, mapper_e1, sample_extraction):
        """Test assessment/diagnosis extraction and mapping."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        diagnosis = response.form_data.get("primary_diagnosis", {})
        
        # Check primary diagnosis
        assert diagnosis.get("diagnosis_description") == "Type 2 Diabetes"
    
    def test_confidence_scoring(self, mapper_e1, sample_extraction):
        """Test confidence score calculation."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        # Confidence should be between 0 and 1
        assert 0 <= response.confidence_score <= 1
        
        # With rich extraction, should be reasonably high
        assert response.confidence_score > 0.5
    
    def test_validation_status_valid(self, mapper_e1, sample_extraction):
        """Test validation status determination."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        # With sufficient fields filled, should be valid or partial
        assert response.validation_status in ["valid", "partial"]
    
    def test_validation_status_invalid(self, mapper_e1):
        """Test validation with minimal data."""
        minimal_extraction = ClinicalExtract(
            extraction_id="EXT_minimal",
            confidence=0.2,
        )
        
        response = mapper_e1.map_audio_extraction(
            minimal_extraction,
            patient_id="P001"
        )
        
        # With minimal data, should be invalid or partial
        assert response.validation_status in ["invalid", "partial"]
    
    def test_auto_filled_fields_tracking(self, mapper_e1, sample_extraction):
        """Test auto-filled fields tracking."""
        response = mapper_e1.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        # Should have auto-filled fields
        assert len(response.auto_filled_fields) > 0
        
        # Should contain expected OASIS field codes
        assert any("M0" in field for field in response.auto_filled_fields)
    
    def test_warnings_on_parse_errors(self, mapper_e1):
        """Test that warnings are generated for unparseable data."""
        extraction_with_bad_data = ClinicalExtract(
            extraction_id="EXT_bad",
            vitals=[
                VitalSign(name="blood pressure", value="invalid/data", unit="mmHg"),
            ],
            confidence=0.5,
        )
        
        response = mapper_e1.map_audio_extraction(
            extraction_with_bad_data,
            patient_id="P001"
        )
        
        # Should generate warnings for unparseable BP
        assert len(response.warnings or []) > 0
        assert any("BP" in w or "blood pressure" in w.lower() for w in (response.warnings or []))
    
    def test_map_e2_form(self, mapper_e2, sample_extraction):
        """Test E2 form generation."""
        response = mapper_e2.map_audio_extraction(
            sample_extraction,
            patient_id="P001"
        )
        
        assert response.form_version == "E2"
        assert response.form_data is not None
    
    def test_map_ocr_extraction(self, mapper_e1):
        """Test mapping OCR extraction to OASIS."""
        ocr_extraction = OCRClinicalExtract(
            extraction_id="EXT_ocr123",
            vitals=[
                VitalSign(name="blood pressure", value="120/80", unit="mmHg"),
            ],
            medications=[
                Medication(name="Aspirin", dose="81mg", frequency="daily", route="oral"),
            ],
            extraction_confidence=0.75,
        )
        
        response = mapper_e1.map_ocr_extraction(
            ocr_extraction,
            patient_id="P002"
        )
        
        assert response.extraction_id == "EXT_ocr123"
        assert response.patient_id == "P002"
        assert response.form_data is not None
    
    def test_pain_severity_parsing(self, mapper_e1):
        """Test parsing pain severity from 0-10 scale."""
        extraction = ClinicalExtract(
            extraction_id="EXT_pain",
            symptoms=[
                Symptom(name="pain 7/10", severity=7),
            ],
            confidence=0.8,
        )
        
        response = mapper_e1.map_audio_extraction(
            extraction,
            patient_id="P001"
        )
        
        pain = response.form_data.get("pain_assessment", {})
        assert pain.get("pain_present") == "1"
        assert pain.get("pain_severity") == 7
    
    def test_functional_assessment_parsing(self, mapper_e1):
        """Test parsing functional status from symptoms."""
        extraction = ClinicalExtract(
            extraction_id="EXT_functional",
            symptoms=[
                Symptom(name="unable to ambulate without assistance", severity=5),
            ],
            confidence=0.8,
        )
        
        response = mapper_e1.map_audio_extraction(
            extraction,
            patient_id="P001"
        )
        
        functional = response.form_data.get("functional_assessment", {})
        # Should parse as unable (2)
        assert functional.get("ambulation") == "2"
    
    def test_mental_health_assessment(self, mapper_e1):
        """Test mental health assessment mapping."""
        extraction = ClinicalExtract(
            extraction_id="EXT_mental",
            symptoms=[
                Symptom(name="depression moderate", severity=5),
                Symptom(name="anxiety severe", severity=8),
            ],
            confidence=0.8,
        )
        
        response = mapper_e1.map_audio_extraction(
            extraction,
            patient_id="P001"
        )
        
        mental = response.form_data.get("mental_health", {})
        # Should capture depression and anxiety
        assert mental.get("depression_severity") is not None
        assert mental.get("anxiety_level") is not None
    
    def test_batch_processing(self, mapper_e1, sample_extraction):
        """Test processing multiple extractions."""
        extractions = [sample_extraction for _ in range(3)]
        
        responses = []
        for i, extraction in enumerate(extractions):
            extraction.extraction_id = f"EXT_batch_{i}"
            response = mapper_e1.map_audio_extraction(
                extraction,
                patient_id=f"P_{i:03d}"
            )
            responses.append(response)
        
        # Should generate responses for all extractions
        assert len(responses) == 3
        assert all(isinstance(r, OASISPrefillResponse) for r in responses)
    
    def test_mapper_reset(self, mapper_e1, sample_extraction):
        """Test mapper reset functionality."""
        # First mapping
        mapper_e1.map_audio_extraction(sample_extraction, patient_id="P001")
        
        # Get state
        first_filled = len(mapper_e1.auto_filled_fields)
        
        # Reset
        mapper_e1.reset()
        
        # Should be cleared
        assert len(mapper_e1.auto_filled_fields) == 0
        assert len(mapper_e1.confidence_scores) == 0
        assert len(mapper_e1.warnings) == 0


class TestOASISValidation:
    """Test OASIS form validation."""
    
    @pytest.fixture
    def mapper(self):
        """Create mapper."""
        return OASISMapper(form_version="E1")
    
    def test_response_structure(self, mapper):
        """Test response has all required fields."""
        extraction = ClinicalExtract(
            extraction_id="EXT_test",
            confidence=0.8,
        )
        
        response = mapper.map_audio_extraction(extraction, patient_id="P001")
        
        # Check all required fields present
        assert response.extraction_id is not None
        assert response.patient_id is not None
        assert response.form_version is not None
        assert response.form_data is not None
        assert response.validation_status is not None
        assert response.confidence_score is not None
        assert response.generated_at is not None
        assert response.generation_time_ms is not None
    
    def test_confidence_bounds(self, mapper):
        """Test confidence score is always 0-1."""
        extractions = [
            ClinicalExtract(extraction_id="EXT_1", confidence=0.0),
            ClinicalExtract(extraction_id="EXT_2", confidence=0.5),
            ClinicalExtract(extraction_id="EXT_3", confidence=1.0),
        ]
        
        for extraction in extractions:
            response = mapper.map_audio_extraction(extraction, patient_id="P001")
            assert 0 <= response.confidence_score <= 1
    
    def test_timestamp_accuracy(self, mapper):
        """Test timestamps are reasonable."""
        extraction = ClinicalExtract(extraction_id="EXT_test", confidence=0.8)
        
        response = mapper.map_audio_extraction(extraction, patient_id="P001")
        
        # Generated time should be a datetime
        assert isinstance(response.generated_at, datetime)
        
        # Generation time should be reasonable (< 10 seconds)
        assert 0 < response.generation_time_ms < 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
