"""
OASIS-E1 and OASIS-E2 data models and templates.
Complete HIPAA-compliant clinical assessment forms.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import date, datetime
from enum import Enum


class YesNoResponse(str, Enum):
    """Standard yes/no response."""
    YES = "1"
    NO = "0"
    UNKNOWN = "9"


class ResponseOption(str, Enum):
    """Standard OASIS response format."""
    RESPONSE_0 = "0"
    RESPONSE_1 = "1"
    RESPONSE_2 = "2"
    RESPONSE_3 = "3"
    RESPONSE_4 = "4"
    RESPONSE_9 = "9"  # Unknown


# ============================================================================
# OASIS-E1 / E2 Common Models
# ============================================================================

class PatientInformation(BaseModel):
    """M0000 - M0100 series: Patient identifying information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0010: CMS Certification ID
    cms_certification_id: Optional[str] = Field(None, alias="M0010")
    
    # M0020: Patient ID
    patient_id: Optional[str] = Field(..., alias="M0020", description="Patient identifying number or medical record number")
    
    # M0030: Patient name
    patient_name: Optional[str] = Field(None, alias="M0030")
    
    # M0040: Patient street address
    patient_address: Optional[str] = Field(None, alias="M0040")
    
    # M0050: Patient phone number
    patient_phone: Optional[str] = Field(None, alias="M0050")
    
    # M0060: Date of birth
    date_of_birth: Optional[date] = Field(None, alias="M0060")
    
    # M0070: Sex
    sex: Optional[Literal["1", "2"]] = Field(None, alias="M0070", description="1=Male, 2=Female")


class AdmissionInformation(BaseModel):
    """M0090 - M0150 series: Admission assessment information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0090: Date of referral
    date_of_referral: Optional[date] = Field(None, alias="M0090")
    
    # M0100: Response to referral
    response_to_referral: Optional[str] = Field(None, alias="M0100", description="0=No response, 1=Contact unable, 2=Refused")
    
    # M0110: Reason for no response/referral
    reason_for_no_response: Optional[str] = Field(None, alias="M0110")
    
    # M0120: Reason for discharge
    reason_for_discharge: Optional[str] = Field(None, alias="M0120")
    
    # M0130: Follow-up planned
    follow_up_planned: Optional[YesNoResponse] = Field(None, alias="M0130")
    
    # M0140: Follow-up date
    follow_up_date: Optional[date] = Field(None, alias="M0140")
    
    # M0150: Episode timing
    episode_timing: Optional[str] = Field(None, alias="M0150", description="1=Admit, 2=Follow-up, 3=D/C")


class ClinicalVitalSigns(BaseModel):
    """M0500 series: Vital signs and physical measurements."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0500: Blood pressure
    blood_pressure_systolic: Optional[int] = Field(None, alias="M0500_Systolic")
    blood_pressure_diastolic: Optional[int] = Field(None, alias="M0500_Diastolic")
    
    # M0510: Pulse rate
    pulse_rate: Optional[int] = Field(None, alias="M0510", description="Beats per minute")
    
    # M0520: Respiratory rate
    respiratory_rate: Optional[int] = Field(None, alias="M0520", description="Breaths per minute")
    
    # M0530: Temperature
    temperature: Optional[float] = Field(None, alias="M0530", description="Degrees Fahrenheit")
    
    # M0540: Weight
    weight: Optional[float] = Field(None, alias="M0540", description="Pounds")
    
    # M0550: Height
    height: Optional[float] = Field(None, alias="M0550", description="Inches")
    
    # M0560: BMI
    bmi: Optional[float] = Field(None, alias="M0560")


class PrimaryDiagnosis(BaseModel):
    """M0700 - M0750 series: Primary diagnosis information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0700: Primary diagnosis code
    diagnosis_code: Optional[str] = Field(None, alias="M0700", description="ICD-10 code")
    
    # M0710: Primary diagnosis description
    diagnosis_description: Optional[str] = Field(None, alias="M0710")
    
    # M0720: Symptom onset
    symptom_onset_date: Optional[date] = Field(None, alias="M0720")
    
    # M0730: Related diagnosis codes
    related_diagnosis_codes: List[str] = Field(default_factory=list, alias="M0730")
    
    # M0740: Related diagnosis descriptions
    related_diagnosis_descriptions: List[str] = Field(default_factory=list, alias="M0740")


class MedicationInformation(BaseModel):
    """M0800 series: Medication information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0800: Number of medications
    number_of_medications: Optional[int] = Field(None, alias="M0800")
    
    # M0810: Medication list
    medications: List[Dict[str, str]] = Field(
        default_factory=list,
        alias="M0810",
        description="List of medication objects with name, dose, frequency, route"
    )


class FunctionalAssessment(BaseModel):
    """M0900 - M1000 series: Functional status and ADL assessment."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M0900: Ambulation/locomotion
    ambulation: Optional[str] = Field(None, alias="M0900", description="0=Able, 1=Uses device, 2=Unable, 9=Unknown")
    
    # M0910: Transfer
    transfer: Optional[str] = Field(None, alias="M0910", description="0=Able, 1=Uses device, 2=Unable, 9=Unknown")
    
    # M0920: Feeding
    feeding: Optional[str] = Field(None, alias="M0920", description="0=Able, 1=Uses device, 2=Unable, 9=Unknown")
    
    # M0930: Toileting
    toileting: Optional[str] = Field(None, alias="M0930")
    
    # M0940: Personal hygiene
    personal_hygiene: Optional[str] = Field(None, alias="M0940")
    
    # M0950: Dressing
    dressing: Optional[str] = Field(None, alias="M0950")
    
    # M0960: Bathing
    bathing: Optional[str] = Field(None, alias="M0960")
    
    # M0970: Cognitive functioning
    cognitive_functioning: Optional[str] = Field(None, alias="M0970", description="0=Oriented, 1=Oriented to person/place, 2=Not oriented, 9=Unknown")


class MentalHealthAssessment(BaseModel):
    """M1100 - M1200 series: Mental health and psychiatric information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M1100: Cognitive function
    cognitive_function: Optional[str] = Field(None, alias="M1100")
    
    # M1110: Anxiety level
    anxiety_level: Optional[str] = Field(None, alias="M1110", description="0=None, 1=Mild, 2=Moderate, 3=Severe, 9=Unknown")
    
    # M1120: Depression screening
    depression_screening: Optional[str] = Field(None, alias="M1120", description="PHQ-2 or other screening")
    
    # M1130: Depression severity
    depression_severity: Optional[str] = Field(None, alias="M1130", description="0=None, 1=Mild, 2=Moderate, 3=Severe")
    
    # M1200: Psychiatric diagnosis
    psychiatric_diagnosis: Optional[str] = Field(None, alias="M1200")


class WoundAssessment(BaseModel):
    """M1300 - M1400 series: Wounds and pressure ulcers."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M1300: Pressure ulcer(s)
    pressure_ulcer_present: Optional[YesNoResponse] = Field(None, alias="M1300")
    
    # M1310: Pressure ulcer count
    pressure_ulcer_count: Optional[int] = Field(None, alias="M1310")
    
    # M1320: Pressure ulcer stage
    pressure_ulcer_stages: List[str] = Field(default_factory=list, alias="M1320", description="List of stages: 1, 2, 3, 4, unstageable")
    
    # M1400: Other wounds
    other_wounds_present: Optional[YesNoResponse] = Field(None, alias="M1400")
    
    # M1410: Other wound descriptions
    other_wound_descriptions: List[str] = Field(default_factory=list, alias="M1410")


class OxygenTreatment(BaseModel):
    """M1500 series: Oxygen and respiratory treatment."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M1500: Oxygen therapy
    oxygen_therapy: Optional[YesNoResponse] = Field(None, alias="M1500")
    
    # M1510: Oxygen device
    oxygen_device: Optional[str] = Field(None, alias="M1510", description="0=Nasal cannula, 1=Face mask, 2=Ventilator, 9=Other")
    
    # M1520: Oxygen hours per day
    oxygen_hours_per_day: Optional[str] = Field(None, alias="M1520")


class PainAssessment(BaseModel):
    """M1600 series: Pain assessment."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M1600: Pain presence
    pain_present: Optional[YesNoResponse] = Field(None, alias="M1600")
    
    # M1610: Pain frequency
    pain_frequency: Optional[str] = Field(None, alias="M1610", description="0=None, 1=Rarely, 2=Occasionally, 3=Frequently, 4=Almost constantly")
    
    # M1620: Pain severity
    pain_severity: Optional[int] = Field(None, alias="M1620", description="0-10 scale")
    
    # M1630: Pain intervention
    pain_intervention: Optional[str] = Field(None, alias="M1630")


class ClinicalRecapitulation(BaseModel):
    """M2000 - M2100 series: Clinical recapitulation and therapies."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M2000: Skilled nursing
    skilled_nursing_needed: Optional[YesNoResponse] = Field(None, alias="M2000")
    
    # M2010: Physical therapy
    physical_therapy_needed: Optional[YesNoResponse] = Field(None, alias="M2010")
    
    # M2020: Occupational therapy
    occupational_therapy_needed: Optional[YesNoResponse] = Field(None, alias="M2020")
    
    # M2030: Speech-language pathology
    speech_therapy_needed: Optional[YesNoResponse] = Field(None, alias="M2030")
    
    # M2040: Medical social services
    medical_social_services_needed: Optional[YesNoResponse] = Field(None, alias="M2040")
    
    # M2050: Home health aide
    home_health_aide_needed: Optional[YesNoResponse] = Field(None, alias="M2050")


class PlanOfCare(BaseModel):
    """M3000 - M3200 series: Plan of care and goals."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M3000: Rehabilitation potential
    rehabilitation_potential: Optional[str] = Field(None, alias="M3000", description="0=Good, 1=Fair, 2=Poor, 9=Unknown")
    
    # M3010: Skilled nursing goal
    skilled_nursing_goal: Optional[str] = Field(None, alias="M3010")
    
    # M3020: Therapy goal
    therapy_goal: Optional[str] = Field(None, alias="M3020")
    
    # M3030: Patient goal
    patient_goal: Optional[str] = Field(None, alias="M3030")
    
    # M3100: Frequency of skilled services
    frequency_skilled_services: Optional[str] = Field(None, alias="M3100", description="Times per week")
    
    # M3200: Duration of services
    duration_services: Optional[str] = Field(None, alias="M3200", description="Estimated number of weeks")


class DischargeInformation(BaseModel):
    """M4000 - M4100 series: Discharge information."""
    model_config = ConfigDict(populate_by_name=True)
    
    # M4000: Reason for discharge
    discharge_reason: Optional[str] = Field(None, alias="M4000")
    
    # M4010: Discharge status
    discharge_status: Optional[str] = Field(None, alias="M4010", description="1=Improved, 2=Discharged as planned, 3=Discharged early")
    
    # M4020: Disposition of patient
    patient_disposition: Optional[str] = Field(None, alias="M4020", description="1=Home, 2=Hospital, 3=Skilled facility, etc.")


# ============================================================================
# Complete OASIS-E1 Form
# ============================================================================

class OASISFormE1(BaseModel):
    """Complete OASIS-E1 assessment form."""
    model_config = ConfigDict(populate_by_name=True)
    
    # Form metadata
    form_version: str = "E1"
    form_completion_date: datetime
    clinician_name: Optional[str] = None
    clinician_id: Optional[str] = None
    
    # Clinical sections
    patient_information: PatientInformation
    admission_information: AdmissionInformation
    vital_signs: ClinicalVitalSigns
    primary_diagnosis: PrimaryDiagnosis
    medications: MedicationInformation
    functional_assessment: FunctionalAssessment
    mental_health: MentalHealthAssessment
    wound_assessment: WoundAssessment
    oxygen_treatment: OxygenTreatment
    pain_assessment: PainAssessment
    clinical_recap: ClinicalRecapitulation
    plan_of_care: PlanOfCare
    discharge_information: Optional[DischargeInformation] = None
    
    # Additional clinical notes
    assessment_notes: Optional[str] = None
    clinical_summary: Optional[str] = None


# ============================================================================
# Complete OASIS-E2 Form
# ============================================================================

class OASISFormE2(OASISFormE1):
    """Complete OASIS-E2 assessment form (extends E1)."""
    
    form_version: str = "E2"
    
    # E2-specific fields
    e2_functional_limitation: Optional[str] = Field(None, description="Enhanced functional assessment")
    e2_cognitive_status: Optional[str] = Field(None, description="Enhanced cognitive assessment")
    e2_behavioral_health: Optional[str] = Field(None, description="Behavioral health tracking")


# ============================================================================
# Prefill Response Model
# ============================================================================

class OASISPrefillResponse(BaseModel):
    """API response for OASIS prefill generation."""
    
    extraction_id: str
    patient_id: str
    form_version: Literal["E1", "E2"]
    
    # The generated form
    form_data: Dict[str, Any]
    
    # Validation results
    validation_status: Literal["valid", "partial", "invalid"]
    missing_fields: List[str] = Field(default_factory=list)
    auto_filled_fields: List[str] = Field(default_factory=list)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    
    # Metadata
    generated_at: datetime
    generation_time_ms: int
    
    # Notes
    notes: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Field Mapping Configuration
# ============================================================================

class FieldMapping(BaseModel):
    """Maps clinical extracted data to OASIS fields."""
    
    # Source to target mapping
    source_field: str
    target_oasis_field: str
    data_type: Literal["string", "integer", "float", "date", "list"]
    
    # Transformation rules
    transformation_rule: Optional[str] = None
    validation_rule: Optional[str] = None
    
    # Metadata
    required: bool = False
    confidence_factor: float = Field(1.0, ge=0.0, le=1.0)


# ============================================================================
# Batch Processing
# ============================================================================

class OASISBatchRequest(BaseModel):
    """Request to process multiple extractions."""
    
    extraction_ids: List[str]
    form_version: Literal["E1", "E2"] = "E1"
    include_validation: bool = True
    generate_pdf: bool = False


class OASISBatchResponse(BaseModel):
    """Response for batch OASIS generation."""
    
    batch_id: str
    total_count: int
    successful_count: int
    failed_count: int
    
    results: List[OASISPrefillResponse]
    errors: List[Dict[str, str]] = Field(default_factory=list)
    
    generated_at: datetime
    processing_time_ms: int

