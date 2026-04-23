"""
OASIS field mapper: Maps clinical extracted data to OASIS-E1/E2 forms.
Handles data transformation, validation, and confidence scoring.
"""

import logging
import re
import sys
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
from pathlib import Path

# Handle both relative and absolute imports
try:
    from ..audio_pipeline.models import ClinicalExtract
    from ..ocr_pipeline.models import OCRClinicalExtract
except ImportError:
    # When running as script, add parent to path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from audio_pipeline.models import ClinicalExtract
    from ocr_pipeline.models import OCRClinicalExtract

from .models import (
    OASISFormE1,
    OASISFormE2,
    OASISPrefillResponse,
    PatientInformation,
    AdmissionInformation,
    ClinicalVitalSigns,
    PrimaryDiagnosis,
    MedicationInformation,
    FunctionalAssessment,
    MentalHealthAssessment,
    WoundAssessment,
    OxygenTreatment,
    PainAssessment,
    ClinicalRecapitulation,
    PlanOfCare,
    DischargeInformation,
)


logger = logging.getLogger(__name__)


class OASISMapper:
    """Maps clinical extracted data to OASIS forms."""
    
    def __init__(self, form_version: str = "E1"):
        """
        Initialize mapper.
        
        Args:
            form_version: "E1" or "E2"
        """
        self.form_version = form_version
        self.confidence_scores: Dict[str, float] = {}
        self.missing_fields: List[str] = []
        self.auto_filled_fields: List[str] = []
        self.warnings: List[str] = []
    
    def map_audio_extraction(
        self,
        extraction: ClinicalExtract,
        patient_id: str,
        clinician_name: Optional[str] = None,
    ) -> OASISPrefillResponse:
        """
        Map audio extraction to OASIS form.
        
        Args:
            extraction: Clinical extraction from audio
            patient_id: Patient ID
            clinician_name: Clinician name
        
        Returns:
            OASIS prefill response
        """
        start_time = datetime.now()
        
        try:
            # Create OASIS form sections
            patient_info = self._map_patient_information(extraction, patient_id)
            admission_info = self._map_admission_information(extraction)
            vitals = self._map_vital_signs(extraction)
            diagnosis = self._map_primary_diagnosis(extraction)
            medications = self._map_medications(extraction)
            functional = self._map_functional_assessment(extraction)
            mental_health = self._map_mental_health(extraction)
            wounds = self._map_wound_assessment(extraction)
            oxygen = self._map_oxygen_treatment(extraction)
            pain = self._map_pain_assessment(extraction)
            clinical_recap = self._map_clinical_recap(extraction)
            plan_of_care = self._map_plan_of_care(extraction)
            
            # Create form based on version
            if self.form_version == "E1":
                form = OASISFormE1(
                    form_completion_date=datetime.now(),
                    clinician_name=clinician_name,
                    patient_information=patient_info,
                    admission_information=admission_info,
                    vital_signs=vitals,
                    primary_diagnosis=diagnosis,
                    medications=medications,
                    functional_assessment=functional,
                    mental_health=mental_health,
                    wound_assessment=wounds,
                    oxygen_treatment=oxygen,
                    pain_assessment=pain,
                    clinical_recap=clinical_recap,
                    plan_of_care=plan_of_care,
                    clinical_summary=extraction.chief_complaint or extraction.plan,
                )
            else:
                form = OASISFormE2(
                    form_completion_date=datetime.now(),
                    clinician_name=clinician_name,
                    patient_information=patient_info,
                    admission_information=admission_info,
                    vital_signs=vitals,
                    primary_diagnosis=diagnosis,
                    medications=medications,
                    functional_assessment=functional,
                    mental_health=mental_health,
                    wound_assessment=wounds,
                    oxygen_treatment=oxygen,
                    pain_assessment=pain,
                    clinical_recap=clinical_recap,
                    plan_of_care=plan_of_care,
                    clinical_summary=extraction.chief_complaint or extraction.plan,
                )
            
            # Calculate overall confidence
            overall_confidence = self._calculate_overall_confidence(extraction)
            
            # Determine validation status
            validation_status = self._get_validation_status()
            
            # Calculate time
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return OASISPrefillResponse(
                extraction_id=extraction.extraction_id or "unknown",
                patient_id=patient_id,
                form_version=self.form_version,
                form_data=form.model_dump(exclude_none=True),
                validation_status=validation_status,
                missing_fields=self.missing_fields,
                auto_filled_fields=self.auto_filled_fields,
                confidence_score=overall_confidence,
                generated_at=datetime.now(),
                generation_time_ms=elapsed_ms,
                warnings=self.warnings if self.warnings else None,
            )
        
        except Exception as e:
            logger.error(f"Error mapping to OASIS: {e}")
            raise
    
    def map_ocr_extraction(
        self,
        extraction,  # OCRClinicalExtract
        patient_id: str,
        clinician_name: Optional[str] = None,
    ) -> OASISPrefillResponse:
        """
        Map OCR extraction to OASIS form.
        
        Args:
            extraction: Clinical extraction from OCR
            patient_id: Patient ID
            clinician_name: Clinician name
        
        Returns:
            OASIS prefill response
        """
        # Convert OCR extraction to audio format for consistent mapping
        clinical_extract = ClinicalExtract(
            extraction_id=extraction.extraction_id,
            vitals=extraction.vitals,
            medications=extraction.medications,
            symptoms=extraction.symptoms,
            assessments=extraction.assessments,
            raw_transcript=extraction.raw_transcript,
            confidence=extraction.extraction_confidence,
        )
        
        return self.map_audio_extraction(clinical_extract, patient_id, clinician_name)
    
    # ========================================================================
    # Section Mappers
    # ========================================================================
    
    def _map_patient_information(
        self,
        extraction: ClinicalExtract,
        patient_id: str,
    ) -> PatientInformation:
        """Map to patient information section."""
        return PatientInformation(
            patient_id=patient_id,
            patient_name=None,  # Not typically in clinical extract
            date_of_birth=None,  # Not typically in clinical extract
        )
    
    def _map_admission_information(
        self,
        extraction: ClinicalExtract,
    ) -> AdmissionInformation:
        """Map to admission information section."""
        return AdmissionInformation(
            date_of_referral=date.today(),
            response_to_referral="2" if extraction else None,
            episode_timing="2",  # Follow-up assessment default
        )
    
    def _map_vital_signs(
        self,
        extraction: ClinicalExtract,
    ) -> ClinicalVitalSigns:
        """Map vital signs section."""
        vitals = ClinicalVitalSigns()
        
        if extraction.vitals:
            for vital in extraction.vitals:
                vital_name = vital.name.lower()
                
                if "blood pressure" in vital_name:
                    try:
                        bp_parts = vital.value.split("/")
                        if len(bp_parts) == 2:
                            vitals.blood_pressure_systolic = int(bp_parts[0])
                            vitals.blood_pressure_diastolic = int(bp_parts[1])
                            self.auto_filled_fields.append("M0500")
                    except:
                        self.warnings.append(f"Could not parse BP: {vital.value}")
                
                elif "heart rate" in vital_name or "pulse" in vital_name:
                    try:
                        vitals.pulse_rate = int(vital.value.replace(" bpm", "").split()[0])
                        self.auto_filled_fields.append("M0510")
                    except:
                        pass
                
                elif "temperature" in vital_name:
                    try:
                        vitals.temperature = float(vital.value)
                        self.auto_filled_fields.append("M0530")
                    except:
                        pass
                
                elif "respiration" in vital_name or "respiratory rate" in vital_name:
                    try:
                        vitals.respiratory_rate = int(vital.value.split()[0])
                        self.auto_filled_fields.append("M0520")
                    except:
                        pass
                
                elif "weight" in vital_name:
                    try:
                        vitals.weight = float(vital.value.split()[0])
                        self.auto_filled_fields.append("M0540")
                    except:
                        pass
                
                elif "height" in vital_name:
                    try:
                        vitals.height = float(vital.value.split()[0])
                        self.auto_filled_fields.append("M0550")
                    except:
                        pass
        
        return vitals
    
    def _map_primary_diagnosis(
        self,
        extraction: ClinicalExtract,
    ) -> PrimaryDiagnosis:
        """Map primary diagnosis section."""
        diagnosis = PrimaryDiagnosis()
        
        if extraction.assessments:
            # Use first assessment as primary diagnosis
            primary = extraction.assessments[0]
            diagnosis.diagnosis_description = primary.condition
            self.auto_filled_fields.append("M0710")

            # Add remaining as related
            if len(extraction.assessments) > 1:
                diagnosis.related_diagnosis_descriptions = [a.condition for a in extraction.assessments[1:]]
                self.auto_filled_fields.append("M0740")
        
        return diagnosis
    
    def _map_medications(
        self,
        extraction: ClinicalExtract,
    ) -> MedicationInformation:
        """Map medications section."""
        meds = MedicationInformation()
        
        if extraction.medications:
            meds.number_of_medications = len(extraction.medications)
            meds.medications = [
                {
                    "name": med.name,
                    "dose": med.dosage,
                    "frequency": med.frequency,
                    "route": med.route,
                }
                for med in extraction.medications
            ]
            self.auto_filled_fields.extend(["M0800", "M0810"])
        
        return meds
    
    def _map_functional_assessment(
        self,
        extraction: ClinicalExtract,
    ) -> FunctionalAssessment:
        """Map functional assessment section."""
        functional = FunctionalAssessment()
        
        # Parse symptoms for functional impact
        if extraction.symptoms:
            for symptom in extraction.symptoms:
                symptom_name = symptom.name.lower()
                
                if "ambulation" in symptom_name or "walking" in symptom_name:
                    functional.ambulation = "2" if "unable" in symptom_name else "1" if "difficulty" in symptom_name else "0"
                    self.auto_filled_fields.append("M0900")
                
                elif "transfer" in symptom_name or "mobility" in symptom_name:
                    functional.transfer = "2" if "unable" in symptom_name else "1" if "difficulty" in symptom_name else "0"
                    self.auto_filled_fields.append("M0910")
                
                elif "feeding" in symptom_name or "appetite" in symptom_name:
                    functional.feeding = "2" if "unable" in symptom_name else "0"
                    self.auto_filled_fields.append("M0920")
        
        return functional
    
    def _map_mental_health(
        self,
        extraction: ClinicalExtract,
    ) -> MentalHealthAssessment:
        """Map mental health assessment section."""
        mental = MentalHealthAssessment()
        
        if extraction.symptoms:
            for symptom in extraction.symptoms:
                symptom_name = symptom.name.lower()
                
                if "depression" in symptom_name:
                    mental.depression_severity = "3" if "severe" in symptom_name else "2" if "moderate" in symptom_name else "1"
                    self.auto_filled_fields.append("M1130")
                
                elif "anxiety" in symptom_name:
                    mental.anxiety_level = "3" if "severe" in symptom_name else "2" if "moderate" in symptom_name else "1"
                    self.auto_filled_fields.append("M1110")
        
        return mental
    
    def _map_wound_assessment(
        self,
        extraction: ClinicalExtract,
    ) -> WoundAssessment:
        """Map wound assessment section."""
        wounds = WoundAssessment()
        
        if extraction.symptoms:
            for symptom in extraction.symptoms:
                symptom_name = symptom.name.lower()
                
                if "wound" in symptom_name or "ulcer" in symptom_name or "pressure" in symptom_name:
                    wounds.pressure_ulcer_present = "1"
                    wounds.other_wound_descriptions.append(symptom.name)
                    self.auto_filled_fields.extend(["M1300", "M1410"])
        
        return wounds
    
    def _map_oxygen_treatment(
        self,
        extraction: ClinicalExtract,
    ) -> OxygenTreatment:
        """Map oxygen treatment section."""
        oxygen = OxygenTreatment()
        
        if extraction.symptoms:
            for symptom in extraction.symptoms:
                if "oxygen" in symptom.name.lower():
                    oxygen.oxygen_therapy = "1"
                    self.auto_filled_fields.append("M1500")
        
        return oxygen
    
    def _map_pain_assessment(
        self,
        extraction: ClinicalExtract,
    ) -> PainAssessment:
        """Map pain assessment section."""
        pain = PainAssessment()
        
        if extraction.symptoms:
            pain_symptoms = [s for s in extraction.symptoms if "pain" in s.name.lower()]
            
            if pain_symptoms:
                pain.pain_present = "1"
                
                # Try to extract pain severity (0-10 scale)
                for symptom in pain_symptoms:
                    match = re.search(r"(\d+)/10|(\d+) out of 10", symptom.name)
                    if match:
                        try:
                            pain.pain_severity = int(match.group(1) or match.group(2))
                            self.auto_filled_fields.append("M1620")
                        except:
                            pass
                
                self.auto_filled_fields.append("M1600")
        
        return pain
    
    def _map_clinical_recap(
        self,
        extraction: ClinicalExtract,
    ) -> ClinicalRecapitulation:
        """Map clinical recapitulation section."""
        recap = ClinicalRecapitulation()
        
        # Default to needing skilled nursing
        recap.skilled_nursing_needed = "1"
        self.auto_filled_fields.append("M2000")
        
        return recap
    
    def _map_plan_of_care(
        self,
        extraction: ClinicalExtract,
    ) -> PlanOfCare:
        """Map plan of care section."""
        plan = PlanOfCare()
        
        if extraction.plan:
            plan.skilled_nursing_goal = extraction.plan
            self.auto_filled_fields.append("M3010")
        
        # Default rehabilitation potential to Fair
        plan.rehabilitation_potential = "1"
        self.auto_filled_fields.append("M3000")
        
        return plan
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _calculate_overall_confidence(self, extraction: ClinicalExtract) -> float:
        """
        Calculate overall confidence score for prefilled form.
        
        Args:
            extraction: Clinical extraction
        
        Returns:
            Confidence score (0-1)
        """
        if not extraction:
            return 0.0
        
        # Base confidence from extraction
        base_confidence = extraction.confidence if hasattr(extraction, 'confidence') else 0.5
        
        # Adjust based on number of auto-filled fields
        field_fill_ratio = len(self.auto_filled_fields) / 30  # Estimate ~30 important fields
        field_confidence = min(field_fill_ratio, 1.0)
        
        # Combine scores
        overall = (base_confidence * 0.6) + (field_confidence * 0.4)
        
        logger.debug(f"Confidence calculation: base={base_confidence:.2f}, fields={field_confidence:.2f}, overall={overall:.2f}")
        
        return round(overall, 2)
    
    def _get_validation_status(self) -> str:
        """
        Determine validation status based on filled fields.
        
        Returns:
            "valid", "partial", or "invalid"
        """
        # Require at least 50% of key fields filled for partial
        required_fields = 25
        
        if len(self.auto_filled_fields) >= required_fields:
            return "valid"
        elif len(self.auto_filled_fields) >= required_fields * 0.5:
            return "partial"
        else:
            return "invalid"
    
    def reset(self):
        """Reset mapper state for next mapping."""
        self.confidence_scores = {}
        self.missing_fields = []
        self.auto_filled_fields = []
        self.warnings = []

