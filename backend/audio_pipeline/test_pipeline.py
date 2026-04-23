"""
Unit tests for audio pipeline module.
"""

import pytest
import json
from fastapi.testclient import TestClient
from extractor import ClinicalExtractor
from models import VitalSign, Medication, Symptom, Assessment, ClinicalExtract


class TestClinicalExtractor:
    """Tests for ClinicalExtractor."""
    
    @pytest.fixture
    def extractor(self):
        return ClinicalExtractor()
    
    def test_extract_blood_pressure(self, extractor):
        """Test blood pressure extraction."""
        transcript = "Patient's BP is 120/80 mmHg"
        vitals = extractor.extract_vitals(transcript)
        assert len(vitals) > 0
        assert any(v.name == "Blood Pressure" and "120" in v.value for v in vitals)
    
    def test_extract_heart_rate(self, extractor):
        """Test heart rate extraction."""
        transcript = "Heart rate is 72 bpm"
        vitals = extractor.extract_vitals(transcript)
        assert len(vitals) > 0
        assert any(v.name == "Heart Rate" for v in vitals)
    
    def test_extract_lisinopril(self, extractor):
        """Test medication extraction."""
        transcript = "Patient is taking lisinopril 10mg once daily"
        meds = extractor.extract_medications(transcript)
        assert len(meds) > 0
        assert any("lisinopril" in m.name.lower() for m in meds)
    
    def test_extract_symptom(self, extractor):
        """Test symptom extraction."""
        transcript = "Patient reports chest pain, moderate severity"
        symptoms = extractor.extract_symptoms(transcript)
        assert len(symptoms) > 0
        assert any("pain" in s.name.lower() for s in symptoms)
    
    def test_extract_assessment(self, extractor):
        """Test assessment extraction."""
        transcript = "Diagnosis: hypertension"
        assessments = extractor.extract_assessments(transcript)
        assert len(assessments) > 0
        assert any("hypertension" in a.condition.lower() for a in assessments)
    
    def test_extract_chief_complaint(self, extractor):
        """Test chief complaint extraction."""
        transcript = "Chief complaint: shortness of breath"
        chief = extractor.extract_chief_complaint(transcript)
        assert chief is not None
        assert "breath" in chief.lower()
    
    def test_extract_all(self, extractor):
        """Test full extraction pipeline."""
        transcript = (
            "Chief complaint: chest pain. "
            "Patient reports chest pain for 2 days, moderate severity. "
            "Vitals: BP 140/90, HR 88 bpm, RR 16. "
            "Currently taking lisinopril 10mg daily. "
            "Diagnosis: hypertension. "
            "Plan: will start cardiac workup"
        )
        
        result = extractor.extract_all(transcript)
        
        assert len(result.vitals) > 0
        assert len(result.medications) > 0
        assert len(result.symptoms) > 0
        assert len(result.assessments) > 0
        assert result.chief_complaint is not None
        assert result.plan is not None
        assert result.raw_transcript == transcript


class TestModels:
    """Tests for Pydantic models."""
    
    def test_vital_sign_model(self):
        """Test VitalSign model."""
        vital = VitalSign(
            name="Blood Pressure",
            value="120/80",
            unit="mmHg"
        )
        assert vital.name == "Blood Pressure"
        assert vital.value == "120/80"
        assert vital.unit == "mmHg"
    
    def test_medication_model(self):
        """Test Medication model."""
        med = Medication(
            name="Lisinopril",
            dosage="10mg",
            frequency="once daily",
            route="oral",
            status="active"
        )
        assert med.name == "Lisinopril"
        assert med.dosage == "10mg"
        assert med.status == "active"
    
    def test_clinical_extract_model(self):
        """Test ClinicalExtract model."""
        extract = ClinicalExtract(
            vitals=[],
            medications=[],
            symptoms=[],
            assessments=[],
            raw_transcript="test transcript"
        )
        assert isinstance(extract.vitals, list)
        assert extract.raw_transcript == "test transcript"
    
    def test_model_to_json(self):
        """Test model serialization to JSON."""
        vital = VitalSign(name="HR", value="72", unit="bpm")
        json_str = vital.model_dump_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["name"] == "HR"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
