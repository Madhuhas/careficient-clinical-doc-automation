# Clinical Documentation Automation — Home Health

Home health nurses spend 2–3 hours per visit on paperwork. This project cuts that down by automatically transcribing visit audio, extracting clinical data, and pre-filling OASIS assessment forms — leaving the clinician to review and approve rather than type from scratch.

Built specifically around the Careficient EHR workflow.

---

## The Problem

A typical home health visit goes like this:

1. Nurse visits patient, records vitals, discusses symptoms, adjusts medications
2. Nurse drives to next patient while mentally replaying the visit
3. Nurse spends 45–90 minutes that evening filling out OASIS forms from memory

Errors happen. Burnout happens. Patient care suffers.

This system handles step 3 automatically.

---

## What It Does

```
Audio recording (.mp3/.wav)  ──►  Whisper transcription
Scanned document (.pdf/.png) ──►  Tesseract OCR
                                        │
                                        ▼
                               Clinical extraction
                               (vitals, meds, dx, symptoms)
                                        │
                                        ▼
                               OASIS E1/E2 pre-fill
                               (M-codes, ICD-10, confidence score)
                                        │
                                        ▼
                               Clinician review UI
                               (edit → approve → submit)
```

Real example — from a 20-second audio clip:

```json
{
  "chief_complaint": "shortness of breath",
  "vitals": [
    { "name": "Blood Pressure", "value": "140/90", "unit": "mmHg" },
    { "name": "Heart Rate",     "value": "88",     "unit": "bpm"  }
  ],
  "medications": [
    { "name": "Lasix", "dosage": "40 mg", "frequency": "once daily" }
  ],
  "assessments": [
    { "condition": "CHF", "icd_code": "I50.9", "severity": "Acute" }
  ],
  "oasis_m0100": "shortness of breath",
  "oasis_m0210": "CHF (I50.9) — Acute",
  "oasis_m0270": "Lasix 40 mg once daily"
}
```

---

## Architecture

Three independent FastAPI services + a React review UI:

| Service | Port | Responsibility |
|---|---|---|
| `audio_pipeline` | 8000 | Whisper STT → clinical extraction |
| `ocr_pipeline`   | 8001 | Tesseract OCR → clinical extraction |
| `oasis_prefill`  | 8003 | Maps extracted data → OASIS E1/E2 form |
| `review-ui`      | 3000 | React — clinician reviews and edits output |

Services are intentionally decoupled. You can run just the audio pipeline without the others.

---

## Extraction Provider System

The clinical extraction layer is designed to swap providers without touching any pipeline code:

```
EXTRACTOR_PROVIDER=regex      # deterministic patterns — default, no deps
EXTRACTOR_PROVIDER=ollama     # local LLM via Ollama, free, no API key
EXTRACTOR_PROVIDER=bedrock    # AWS Bedrock (Claude / Titan)
EXTRACTOR_PROVIDER=anthropic  # Anthropic API
```

Every LLM provider falls back to regex automatically if it fails, so clinical workflows are never blocked by a provider outage. The health endpoint shows which provider is active:

```json
{ "extractor": "ready (regex)" }
```

---

## Stack

**Backend**
- Python 3.11, FastAPI, Uvicorn
- OpenAI Whisper (base model, CPU)
- Tesseract + pdf2image for OCR
- Pydantic v2 for data validation
- imageio-ffmpeg (bundled FFmpeg, no system install needed)
- boto3 stubs for AWS (S3, Lambda, Step Functions, DynamoDB)

**Frontend**
- React 18, Axios

**Infrastructure (designed for)**
- AWS Lambda + Step Functions for orchestration
- S3 for document storage
- RDS PostgreSQL for patient records
- KMS encryption, CloudTrail audit logging

---

## Running Locally

**Backend — three terminals:**

```bash
# Terminal 1
cd backend/audio_pipeline
pip install -r requirements.txt
uvicorn app:app --port 8000 --reload

# Terminal 2
cd backend/ocr_pipeline
pip install -r requirements.txt
uvicorn app:app --port 8001 --reload

# Terminal 3
cd backend/oasis_prefill
pip install -r requirements.txt
uvicorn app:app --port 8003 --reload
```

**Frontend:**

```bash
cd frontend/review-ui
npm install && npm start
```

Open [http://localhost:3000](http://localhost:3000). API docs at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

**Switch to a local LLM (no API key needed):**

```bash
# Install Ollama from https://ollama.ai, then:
ollama pull llama3.2
echo "EXTRACTOR_PROVIDER=ollama" >> backend/audio_pipeline/.env
```

---

## Quick Test with Sample Files

The `samples/` directory contains ready-to-use test files so you can exercise the full pipeline without recording anything yourself.

| File | Description |
|---|---|
| `samples/sample_visit.wav` | Synthesized home health nursing visit — CHF patient with vitals, meds, and assessment |
| `samples/sample_clinical_note.png` | Scanned clinical note image with the same visit data for OCR testing |

**Test the audio pipeline:**

```bash
curl -X POST http://localhost:8000/transcribe \
  -F "audio=@samples/sample_visit.wav"
```

Expected output includes BP `148/92`, `Lasix 40 mg`, CHF diagnosis (`I50.9`), and a completed OASIS pre-fill.

**Test the OCR pipeline:**

```bash
curl -X POST http://localhost:8001/ocr \
  -F "document=@samples/sample_clinical_note.png"
```

Returns a `document_id`. Then extract clinical data:

```bash
curl -X POST http://localhost:8001/extract \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<id from above>"}'
```

**Regenerate sample files** (if needed):

```bash
python samples/generate_samples.py
```

---

## Key Design Decisions

**Why three services instead of one?**
Each pipeline can be scaled, deployed, and updated independently. A burst of PDF uploads shouldn't affect audio transcription throughput.

**Why Whisper instead of Amazon Transcribe Medical?**
Whisper runs locally with no per-minute cost during development. The extraction layer is provider-agnostic — swapping to Transcribe Medical is a config change, not a rewrite.

**Why regex + LLM fallback, not LLM-only?**
LLMs are powerful but non-deterministic. For clinical data going into legal medical records, you need predictable behavior. Regex runs fast, produces consistent output, and never hallucinates a blood pressure value. LLMs handle the messy edge cases regex misses. Both outputs go through the same validation layer.

**HIPAA considerations**
- No PHI in logs (transcript IDs only, never patient names or DOBs)
- KMS encryption designed into the AWS architecture
- Audit trail via CloudTrail
- In-memory storage in current build — production uses RDS with row-level encryption

---

## Project Structure

```
backend/
├── audio_pipeline/         # Whisper STT + extraction (port 8000)
│   ├── extraction/
│   │   ├── base.py         # Abstract extractor interface
│   │   ├── llm_extractor.py  # Ollama / Bedrock / Anthropic
│   │   └── factory.py      # get_extractor() — reads EXTRACTOR_PROVIDER
│   ├── extractor.py        # Regex implementation
│   ├── app.py
│   └── models.py
├── ocr_pipeline/           # Tesseract OCR + extraction (port 8001)
├── oasis_prefill/          # OASIS form mapper (port 8003)
│   ├── mapper.py           # 12 section mappers, M-codes, confidence scoring
│   └── models.py           # OASIS-E1/E2 Pydantic models
├── common/                 # Shared utilities, logging, DB, AWS helpers
└── architecture/           # System diagrams and DB schema

frontend/
└── review-ui/              # React clinician review interface

samples/
├── sample_visit.wav            # Synthesized nursing visit audio (CHF patient)
├── sample_clinical_note.png    # Scanned clinical note image for OCR testing
└── generate_samples.py         # Script to regenerate sample files
```

---

## Limitations / Honest Notes

- Whisper base model makes occasional errors on medical terminology ("QD" → "the fourth daily"). Clinical review step exists for exactly this reason.
- OCR accuracy depends on document scan quality.
- AWS services are architected but not deployed — this is a local working prototype.
- Extraction confidence scores are heuristic, not calibrated against a clinical gold standard.

---

## What's Next

- [ ] Connect RDS PostgreSQL (schema in `architecture/db_schema.sql`)
- [ ] Wire AWS Step Functions for end-to-end orchestration
- [ ] Add Amazon Comprehend Medical as an extraction option
- [ ] Expand OASIS field coverage (currently ~40% of E1/E2)
- [ ] FHIR R4 export for EHR integration
