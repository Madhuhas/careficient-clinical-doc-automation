# Oasis Prefill Module
"""
OASIS Prefill Module
Generates pre-filled OASIS-E1/E2 forms from clinical extractions.
"""

from .mapper import OASISMapper
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
    OASISBatchRequest,
    OASISBatchResponse,
)

__all__ = [
    "OASISMapper",
    "OASISFormE1",
    "OASISFormE2",
    "OASISPrefillResponse",
    "PatientInformation",
    "AdmissionInformation",
    "ClinicalVitalSigns",
    "PrimaryDiagnosis",
    "MedicationInformation",
    "FunctionalAssessment",
    "MentalHealthAssessment",
    "WoundAssessment",
    "OxygenTreatment",
    "PainAssessment",
    "ClinicalRecapitulation",
    "PlanOfCare",
    "DischargeInformation",
    "OASISBatchRequest",
    "OASISBatchResponse",
]

