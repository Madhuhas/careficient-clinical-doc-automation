"""
LLM-based clinical extractor with three provider backends.

Set EXTRACTOR_PROVIDER in your .env to switch:
  ollama    — http://localhost:11434  (free, no key needed)
  bedrock   — AWS Bedrock via boto3   (needs AWS creds + model access)
  anthropic — Anthropic API           (needs ANTHROPIC_API_KEY)

All providers fall back to regex automatically if they fail, so
clinical workflows are never blocked by a network or config issue.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from audio_pipeline.models import Assessment, ClinicalExtract, Medication, Symptom, VitalSign
from audio_pipeline.extraction.base import ClinicalExtractorBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are a clinical documentation assistant for US home-health nursing visits. "
    "Read the transcript and return ONLY a JSON object — no markdown, no explanation."
)

_USER = """\
Extract all clinical data from the transcript below.

Return exactly this JSON structure (omit fields that aren't mentioned, use null for unknowns):

{{
  "vitals": [
    {{"name": "Blood Pressure", "value": "140/90", "unit": "mmHg"}},
    {{"name": "Heart Rate", "value": "88", "unit": "bpm"}}
  ],
  "medications": [
    {{"name": "Lasix", "dosage": "40 mg", "frequency": "once daily", "route": "oral", "status": "active"}}
  ],
  "symptoms": [
    {{"name": "Shortness Of Breath", "severity": null, "duration": null, "location": null}}
  ],
  "assessments": [
    {{"condition": "CHF", "icd_code": "I50.9", "severity": "Acute"}}
  ],
  "chief_complaint": "shortness of breath",
  "plan": null
}}

Rules:
- Blood pressure as "systolic/diastolic" (e.g. "140/90")
- Assessment severity: "Acute", "Severe", "Moderate", "Mild", or null
- ICD-10 codes where confident (CHF→I50.9, HTN→I10, COPD→J44.9, DM→E11.9)
- chief_complaint: the patient's main reason for this visit

Transcript:
{transcript}
"""


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class _OllamaProvider:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")

    def complete(self, system: str, user: str) -> str:
        import requests
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": f"{system}\n\n{user}", "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"]

    def __repr__(self):
        return f"Ollama({self.model} @ {self.base_url})"


class _BedrockProvider:
    """AWS Bedrock — Claude 3 Sonnet by default."""

    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import boto3
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def complete(self, system: str, user: str) -> str:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2048,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        })
        resp = self.client.invoke_model(
            modelId=self.model_id, body=body,
            contentType="application/json", accept="application/json",
        )
        return json.loads(resp["body"].read())["content"][0]["text"]

    def __repr__(self):
        return f"Bedrock({self.model_id})"


class _AnthropicProvider:
    def __init__(self):
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError("Run: pip install anthropic")
            self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return self._client

    def complete(self, system: str, user: str) -> str:
        msg = self.client.messages.create(
            model=self.model, max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

    def __repr__(self):
        return f"Anthropic({self.model})"


_PROVIDERS = {"ollama": _OllamaProvider, "bedrock": _BedrockProvider, "anthropic": _AnthropicProvider}


# ---------------------------------------------------------------------------
# LLM extractor
# ---------------------------------------------------------------------------

class LLMClinicalExtractor(ClinicalExtractorBase):
    """Wraps any LLM provider and converts its JSON output to ClinicalExtract."""

    def __init__(self, provider: str = "ollama"):
        if provider not in _PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Choose: {', '.join(_PROVIDERS)}")
        self._provider_name = provider
        self._provider = _PROVIDERS[provider]()
        logger.info(f"LLM extractor: {self._provider}")

    @property
    def provider_name(self) -> str:
        return f"llm:{self._provider_name}"

    def extract_all(self, transcript: str) -> ClinicalExtract:
        from audio_pipeline.extractor import ClinicalExtractor
        return self.extract_with_fallback(transcript, fallback=ClinicalExtractor())

    def extract_with_fallback(self, transcript: str, fallback=None):
        try:
            return self._call_and_parse(transcript)
        except Exception as exc:
            logger.warning(f"[{self.provider_name}] failed: {exc}. Using regex fallback.")
            if fallback:
                return fallback.extract_all(transcript)
            raise

    def _call_and_parse(self, transcript: str) -> ClinicalExtract:
        raw = self._provider.complete(_SYSTEM, _USER.format(transcript=transcript))
        logger.debug(f"LLM raw: {raw[:200]}")
        data = self._parse_json(raw)
        return self._to_extract(data, transcript)

    def _parse_json(self, raw: str) -> dict:
        # Strip markdown fences if the model wraps output in ```json ... ```
        cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("`").strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    def _to_extract(self, data: dict, transcript: str) -> ClinicalExtract:
        vitals = [
            VitalSign(name=v["name"], value=str(v["value"]), unit=v.get("unit"))
            for v in (data.get("vitals") or []) if v.get("value")
        ]
        medications = [
            Medication(name=m["name"], dosage=m.get("dosage"), frequency=m.get("frequency"),
                       route=m.get("route"), status=m.get("status", "active"))
            for m in (data.get("medications") or []) if m.get("name")
        ]
        symptoms = [
            Symptom(name=s["name"], severity=s.get("severity"),
                    duration=s.get("duration"), location=s.get("location"))
            for s in (data.get("symptoms") or []) if s.get("name")
        ]
        assessments = [
            Assessment(condition=a["condition"], icd_code=a.get("icd_code"),
                       severity=a.get("severity"), confidence=0.85)
            for a in (data.get("assessments") or []) if a.get("condition")
        ]
        filled = sum(bool(x) for x in [vitals, medications, symptoms, assessments])
        return ClinicalExtract(
            vitals=vitals, medications=medications, symptoms=symptoms,
            assessments=assessments,
            chief_complaint=data.get("chief_complaint"),
            plan=data.get("plan"),
            raw_transcript=transcript,
            extraction_confidence=round(0.70 + (filled / 4) * 0.25, 2),
        )
