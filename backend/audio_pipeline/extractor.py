"""
Clinical data extractor for parsing transcripts.
Extracts vital signs, medications, symptoms, and assessments using regex patterns
and heuristics. Can be extended with LLM-based extraction for higher accuracy.
"""

import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from .models import VitalSign, Medication, Symptom, Assessment, ClinicalExtract
from .extraction.base import ClinicalExtractorBase


logger = logging.getLogger(__name__)


# ICD-10 code lookup for common clinical conditions
_ICD10_LOOKUP: Dict[str, str] = {
    'chf': 'I50.9',
    'congestive heart failure': 'I50.9',
    'hypertension': 'I10',
    'hypertensive': 'I10',
    'high blood pressure': 'I10',
    'diabetes': 'E11.9',
    'diabetic': 'E11.9',
    'copd': 'J44.9',
    'chronic obstructive': 'J44.9',
    'asthma': 'J45.909',
    'pneumonia': 'J18.9',
    'mi': 'I21.9',
    'myocardial infarction': 'I21.9',
    'heart attack': 'I21.9',
    'gerd': 'K21.0',
    'acid reflux': 'K21.0',
    'arthritis': 'M19.90',
    'depression': 'F32.9',
    'anxiety': 'F41.9',
    'hypothyroidism': 'E03.9',
    'atrial fibrillation': 'I48.91',
    'afib': 'I48.91',
    'uti': 'N39.0',
    'urinary tract infection': 'N39.0',
    'anemia': 'D64.9',
    'dehydration': 'E86.0',
    'ckd': 'N18.9',
    'kidney disease': 'N18.9',
    'renal': 'N18.9',
    'infection': 'A49.9',
    'fracture': 'M84.40',
    'pneumonitis': 'J68.9',
}

# Context words that indicate severity for an assessment
_SEVERITY_CONTEXT = {
    'Acute':    ['flare', 'exacerbation', 'acute', 'decompensated', 'decompensation', 'crisis'],
    'Severe':   ['severe', 'critical', 'end-stage', 'stage 4', 'stage iv'],
    'Moderate': ['moderate', 'worsening', 'uncontrolled', 'poorly controlled'],
    'Mild':     ['mild', 'stable', 'controlled', 'compensated'],
}


class ClinicalExtractor(ClinicalExtractorBase):
    """
    Regex-based clinical extractor (default provider).

    Deterministic, zero-latency, no external dependencies.
    Used directly in production and as the fallback when LLM providers fail.
    """

    @property
    def provider_name(self) -> str:
        return "regex"
    
    def __init__(self):
        """Initialize extraction patterns for various clinical entities."""
        
        # Vital signs patterns - matches various formats
        self.vital_patterns = {
            'Blood Pressure': {
                # support both "140/90" and "140 over 90" (common in voice transcripts)
                'pattern': r'(?:BP|blood pressure)[:\s]+(\d+)\s*(?:[/\\]|over)\s*(\d+)',
                'unit': 'mmHg'
            },
            'Heart Rate': {
                'pattern': r'(?:heart rate|HR|pulse)[:\s]+(\d+)\s*(?:bpm)?',
                'unit': 'bpm'
            },
            'Respiratory Rate': {
                'pattern': r'(?:respiratory rate|RR|respiration)[:\s]+(\d+)',
                'unit': 'breaths/min'
            },
            'Temperature': {
                'pattern': r'(?:temperature|temp)[:\s]+(\d+(?:\.\d+)?)\s*(?:F|°F|Fahrenheit)?',
                'unit': '°F'
            },
            'SpO2': {
                'pattern': r'(?:SpO2|O2 saturation|oxygen saturation)[:\s]+(\d+)\s*%',
                'unit': '%'
            },
            'Weight': {
                'pattern': r'(?:weight|wt)[:\s]+(\d+(?:\.\d+)?)\s*(?:kg|lbs|pounds)',
                'unit': 'lbs'
            },
            'Height': {
                'pattern': r'(?:height|ht)[:\s]+(\d+)[\s\'\"]*(\d+)?',
                'unit': 'inches'
            }
        }
        
        # Medication extraction keywords
        self.medication_keywords = [
            'take', 'taking', 'on', 'prescribed', 'started', 'discontinued',
            'stopped', 'give', 'given', 'administer', 'dose'
        ]
        
        # Common medications for fuzzy matching (generic + common brand names)
        self.common_medications = {
            'lisinopril', 'atorvastatin', 'metformin', 'aspirin', 'ibuprofen',
            'amoxicillin', 'sertraline', 'omeprazole', 'levothyroxine', 'metoprolol',
            'amlodipine', 'simvastatin', 'albuterol', 'loratadine', 'cetirizine',
            'penicillin', 'doxycycline', 'warfarin', 'insulin', 'glucosamine',
            # diuretics / cardiology
            'furosemide', 'lasix', 'torsemide', 'bumetanide', 'hydrochlorothiazide',
            'spironolactone', 'carvedilol', 'atenolol', 'bisoprolol',
            # anticoagulants / antiplatelets
            'clopidogrel', 'rivaroxaban', 'apixaban', 'heparin', 'enoxaparin',
            # antibiotics
            'azithromycin', 'ciprofloxacin', 'levofloxacin', 'vancomycin',
            # respiratory
            'prednisone', 'prednisolone', 'budesonide', 'tiotropium', 'salmeterol',
            # pain / other
            'acetaminophen', 'tramadol', 'gabapentin', 'pregabalin', 'morphine',
            'oxycodone', 'hydrocodone', 'ondansetron', 'pantoprazole',
        }
        
        # Dosage patterns
        self.dosage_pattern = r'(\d+(?:\.\d+)?)\s*(?:mg|ml|g|units|tabs?|tablets?|capsules?|IU|mcg)'
        
        # Frequency patterns
        self.frequency_patterns = {
            'once daily': r'(?:once|one time)\s+daily|qd|q24h|\bdaily\b',
            'twice daily': r'(?:twice|two times)\s+daily|bid|q12h',
            'three times daily': r'(?:three times)\s+daily|tid|q8h',
            'four times daily': r'four times\s+daily|qid|q6h',
            'as needed': r'as needed|prn|when needed',
            'every 4 hours': r'(?:every|q)\s+4\s*(?:hours|h)',
            'every 6 hours': r'(?:every|q)\s+6\s*(?:hours|h)',
            'every 8 hours': r'(?:every|q)\s+8\s*(?:hours|h)',
        }
        
        # Routes of administration
        self.route_patterns = {
            'oral': r'by mouth|PO|orally',
            'intravenous': r'IV|intravenously',
            'intramuscular': r'IM|intramuscularly',
            'subcutaneous': r'SC|SQ|subcutaneously',
            'topical': r'topically|on skin',
            'inhaled': r'inhaled|by inhalation',
        }
        
        # Symptom patterns - common clinical symptoms
        self.symptom_patterns = r'(?:complains|reports|presents|experiencing|has|with|denies)\s+(?:of\s+)?([a-zA-Z\s]+?)(?:\s+(?:for|since|the last|during)|\.|,|and|but|or|$)'
        
        # Symptom keywords to extract
        self.symptom_keywords = [
            'pain', 'ache', 'soreness', 'tenderness',
            'shortness of breath', 'dyspnea', 'SOB',
            'cough', 'coughing',
            'fever', 'chills',
            'nausea', 'vomiting', 'n/v',
            'dizziness', 'vertigo',
            'fatigue', 'tired', 'weakness',
            'headache', 'migraine',
            'rash', 'itching', 'pruritus',
            'swelling', 'edema',
            'constipation', 'diarrhea',
            'chest pain', 'chest discomfort',
            'back pain', 'neck pain',
            'joint pain', 'arthralgia',
            'muscle pain', 'myalgia',
            'sore throat', 'pharyngitis'
        ]
        
        # Assessment/diagnosis patterns - common diagnoses
        self.assessment_keywords = [
            'hypertension', 'hypertensive', 'high blood pressure',
            'diabetes', 'diabetic',
            'COPD', 'chronic obstructive',
            'asthma', 'asthmatic',
            'pneumonia',
            'CHF', 'congestive heart failure',
            'MI', 'myocardial infarction', 'heart attack',
            'GERD', 'acid reflux',
            'arthritis',
            'depression', 'anxiety',
            'hypothyroidism', 'thyroid',
            'infection', 'pneumonitis',
            'fracture', 'broken',
            'sprain', 'strain',
            'dehydration',
            'anemia',
            'UTI', 'urinary tract infection',
            'kidney disease', 'renal',
            'liver disease', 'hepatic',
        ]
        
        # Chief complaint keywords
        self.chief_complaint_keywords = [
            'chief complaint', 'cc:', 'reason for visit',
            'presenting with', 'here for', 'comes in with',
            'complaining of', 'complains of', 'presenting complaint',
            'patient presents', 'patient is complaining',
        ]
        
    def extract_vitals(self, transcript: str) -> List[VitalSign]:
        """Extract vital signs from transcript."""
        vitals = []
        transcript_lower = transcript.lower()
        
        for vital_name, config in self.vital_patterns.items():
            pattern = config['pattern']
            unit = config.get('unit', '')
            
            matches = re.finditer(pattern, transcript_lower, re.IGNORECASE)
            for match in matches:
                groups = match.groups()
                
                if vital_name == 'Blood Pressure' and len(groups) >= 2:
                    value = f"{groups[0]}/{groups[1]}"
                elif vital_name == 'Height' and len(groups) >= 2 and groups[1]:
                    value = f"{groups[0]}'{groups[1]}\""
                else:
                    value = groups[0] if groups else match.group(0)
                
                vital = VitalSign(
                    name=vital_name,
                    value=value.strip(),
                    unit=unit,
                    reference_range=self._get_normal_range(vital_name)
                )
                vitals.append(vital)
                logger.debug(f"Extracted vital: {vital_name} = {value} {unit}")
        
        return vitals
    
    def _get_normal_range(self, vital_name: str) -> Optional[str]:
        """Return normal reference range for vital signs."""
        ranges = {
            'Blood Pressure': '< 120/80 mmHg',
            'Heart Rate': '60-100 bpm',
            'Respiratory Rate': '12-20 breaths/min',
            'Temperature': '98.6°F (37°C)',
            'SpO2': '> 95%',
        }
        return ranges.get(vital_name)
    
    def extract_medications(self, transcript: str) -> List[Medication]:
        """Extract medications and dosing information from transcript."""
        medications = []
        transcript_lower = transcript.lower()
        
        # Find medication mentions
        med_matches = set()

        # Primary: look for known medication names
        for med_name in self.common_medications:
            if med_name in transcript_lower:
                pattern = rf'[^.!?]*?\b{med_name}\b[^.!?]*[.!?]'
                for match in re.finditer(pattern, transcript, re.IGNORECASE):
                    med_matches.add(match.group(0))

        # Fallback: find any word directly followed by a dosage (catches brand names / unknown drugs)
        # e.g. "LASIX 40 mg", "Tylenol 500mg"
        dosage_proximity = re.finditer(
            r'\b([A-Z][a-zA-Z]{2,})\s+' + self.dosage_pattern,
            transcript,
        )
        for m in dosage_proximity:
            candidate = m.group(1).lower()
            # skip if it looks like a common non-drug word
            skip_words = {'patient', 'blood', 'heart', 'rate', 'temp', 'pain', 'dose',
                          'tablet', 'capsule', 'oral', 'take', 'give', 'administer'}
            if candidate not in skip_words:
                sentence_pattern = rf'[^.!?]*?\b{re.escape(m.group(1))}\b[^.!?]*[.!?]'
                for sm in re.finditer(sentence_pattern, transcript, re.IGNORECASE):
                    med_matches.add(sm.group(0))
        
        # Extract medication details from each match
        for med_sentence in med_matches:
            med_sentence_lower = med_sentence.lower()

            # Find medication name — prefer known list, fall back to word-before-dosage
            med_name = None
            for common_med in self.common_medications:
                if common_med in med_sentence_lower:
                    med_name = common_med.title()
                    break

            if not med_name:
                # Use the capitalized word immediately before a dosage
                fb = re.search(r'\b([A-Z][a-zA-Z]{2,})\s+\d+(?:\.\d+)?\s*(?:mg|ml|g|mcg|units)', med_sentence)
                if fb:
                    med_name = fb.group(1).title()

            if not med_name:
                continue
            
            # Extract dosage
            dosage = None
            dosage_match = re.search(self.dosage_pattern, med_sentence, re.IGNORECASE)
            if dosage_match:
                dosage = dosage_match.group(0)
            
            # Extract frequency
            frequency = None
            for freq_name, freq_pattern in self.frequency_patterns.items():
                if re.search(freq_pattern, med_sentence_lower):
                    frequency = freq_name
                    break
            
            # Extract route
            route = None
            for route_name, route_pattern in self.route_patterns.items():
                if re.search(route_pattern, med_sentence_lower):
                    route = route_name.capitalize()
                    break
            
            # Determine status
            status = 'active'
            if any(word in med_sentence_lower for word in ['discontinued', 'stopped', 'dc\'d', 'hold']):
                status = 'discontinued'
            elif any(word in med_sentence_lower for word in ['started', 'new', 'beginning']):
                status = 'new'
            
            medication = Medication(
                name=med_name,
                dosage=dosage,
                frequency=frequency,
                route=route,
                status=status
            )
            medications.append(medication)
            logger.debug(f"Extracted medication: {med_name} {dosage} {frequency}")
        
        return medications
    
    def extract_symptoms(self, transcript: str) -> List[Symptom]:
        """Extract symptoms from transcript."""
        symptoms = []
        transcript_lower = transcript.lower()
        
        # Look for symptom keywords
        found_symptoms = set()
        
        for symptom_keyword in self.symptom_keywords:
            if symptom_keyword in transcript_lower:
                # Find context around symptom
                pattern = rf'[^.!?]*?\b{re.escape(symptom_keyword)}\b[^.!?]*[.!?]'
                for match in re.finditer(pattern, transcript, re.IGNORECASE):
                    context = match.group(0)
                    found_symptoms.add((symptom_keyword, context))
        
        # Extract details for each symptom
        for symptom_name, context in found_symptoms:
            context_lower = context.lower()
            
            # Extract severity
            severity = None
            severity_keywords = {
                'mild': r'mild|slight|minimal',
                'moderate': r'moderate|medium',
                'severe': r'severe|acute|intense|unbearable'
            }
            for sev_name, sev_pattern in severity_keywords.items():
                if re.search(sev_pattern, context_lower):
                    severity = sev_name.capitalize()
                    break
            
            # Extract duration
            duration = None
            duration_match = re.search(r'(?:for|since|the last|during)\s+([^.!?,]+?)(?:\s*$|[.!?,])', context_lower)
            if duration_match:
                duration = duration_match.group(1).strip()
            
            # Extract location
            location = None
            location_keywords = ['head', 'chest', 'back', 'abdomen', 'leg', 'arm', 'throat', 'stomach', 'joint']
            for loc in location_keywords:
                if loc in context_lower:
                    location = loc.capitalize()
                    break
            
            symptom = Symptom(
                name=symptom_name.title(),
                severity=severity,
                duration=duration,
                location=location
            )
            symptoms.append(symptom)
            logger.debug(f"Extracted symptom: {symptom_name} - severity: {severity}, duration: {duration}")
        
        return symptoms
    
    def extract_assessments(self, transcript: str) -> List[Assessment]:
        """Extract clinical assessments/diagnoses from transcript."""
        assessments = []
        transcript_lower = transcript.lower()
        
        found_conditions = set()

        # Look for assessment keywords (case-insensitive comparison)
        for condition in self.assessment_keywords:
            if condition.lower() in transcript_lower:
                # Find context
                pattern = rf'[^.!?]*?\b{re.escape(condition)}\b[^.!?]*[.!?]'
                for match in re.finditer(pattern, transcript, re.IGNORECASE):
                    context = match.group(0)
                    found_conditions.add((condition, context))
        
        # Extract assessment details
        for condition_name, context in found_conditions:
            context_lower = context.lower()

            # Severity — check context-word buckets in priority order
            severity = None
            for sev_label, keywords in _SEVERITY_CONTEXT.items():
                if any(kw in context_lower for kw in keywords):
                    severity = sev_label
                    break

            # ICD-10 code lookup
            icd_code = _ICD10_LOOKUP.get(condition_name.lower())

            # Preserve uppercase abbreviations (CHF, COPD, MI, etc.); title-case others
            display_name = condition_name if condition_name.isupper() else condition_name.title()
            assessment = Assessment(
                condition=display_name,
                icd_code=icd_code,
                severity=severity,
                confidence=0.7,
            )
            assessments.append(assessment)
            logger.debug(f"Extracted assessment: {condition_name}")
        
        return assessments
    
    def extract_chief_complaint(self, transcript: str) -> Optional[str]:
        """Extract chief complaint from transcript."""
        transcript_lower = transcript.lower()
        
        for keyword in self.chief_complaint_keywords:
            match = re.search(rf'{re.escape(keyword)}[:\s]+([^.!?]+)[.!?]', transcript_lower)
            if match:
                complaint = match.group(1).strip()
                # Trim to the first clause to avoid capturing the whole sentence
                first_clause = re.split(r',\s*(?:vitals|heart|blood|bp|temp|weight|height)', complaint)[0]
                chief_complaint = first_clause.strip().rstrip(',')
                logger.debug(f"Extracted chief complaint: {chief_complaint}")
                return chief_complaint

        # Fallback: use first identified symptom
        symptoms = self.extract_symptoms(transcript)
        if symptoms:
            return symptoms[0].name.lower()

        return None
    
    def extract_plan(self, transcript: str) -> Optional[str]:
        """Extract clinical plan from transcript."""
        # Look for plan-related keywords
        plan_keywords = ['plan is', 'will start', 'will continue', 'recommendations:', 'next steps:']
        transcript_lower = transcript.lower()
        
        for keyword in plan_keywords:
            match = re.search(rf'{re.escape(keyword)}\s+([^.!?]+)[.!?]', transcript_lower)
            if match:
                plan = match.group(1).strip()
                logger.debug(f"Extracted plan: {plan}")
                return plan
        
        return None
    
    def extract_all(self, transcript: str) -> ClinicalExtract:
        """
        Full extraction pipeline - extract all clinical entities from transcript.
        
        Args:
            transcript: The transcribed clinical encounter text
            
        Returns:
            ClinicalExtract: Structured clinical data
        """
        logger.info(f"Starting extraction on transcript of length {len(transcript)}")
        
        clinical_data = ClinicalExtract(
            vitals=self.extract_vitals(transcript),
            medications=self.extract_medications(transcript),
            symptoms=self.extract_symptoms(transcript),
            assessments=self.extract_assessments(transcript),
            chief_complaint=self.extract_chief_complaint(transcript),
            plan=self.extract_plan(transcript),
            raw_transcript=transcript,
            extraction_confidence=self._calculate_confidence(transcript)
        )
        
        logger.info(
            f"Extraction complete: {len(clinical_data.vitals)} vitals, "
            f"{len(clinical_data.medications)} meds, "
            f"{len(clinical_data.symptoms)} symptoms, "
            f"{len(clinical_data.assessments)} assessments"
        )
        
        return clinical_data
    
    def _calculate_confidence(self, transcript: str) -> float:
        """Calculate overall confidence score for extraction."""
        # Simple heuristic: confidence based on transcript length and entity extraction
        if len(transcript) < 100:
            return 0.4
        elif len(transcript) < 500:
            return 0.6
        else:
            return 0.8

