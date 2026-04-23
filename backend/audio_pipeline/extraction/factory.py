"""
Returns the right extractor based on EXTRACTOR_PROVIDER env var.

  regex     — deterministic regex, always available (default)
  ollama    — local Ollama LLM, free, no API key needed
  bedrock   — AWS Bedrock via boto3
  anthropic — Anthropic Claude API
"""

import logging
import os

from audio_pipeline.extraction.base import ClinicalExtractorBase

logger = logging.getLogger(__name__)


def get_extractor(provider: str | None = None) -> ClinicalExtractorBase:
    provider = (provider or os.getenv("EXTRACTOR_PROVIDER", "regex")).lower().strip()

    if provider == "regex":
        from audio_pipeline.extractor import ClinicalExtractor
        logger.info("Extractor: regex")
        return ClinicalExtractor()

    if provider in {"ollama", "bedrock", "anthropic"}:
        from audio_pipeline.extraction.llm_extractor import LLMClinicalExtractor
        logger.info(f"Extractor: LLM / {provider}")
        return LLMClinicalExtractor(provider=provider)

    raise ValueError(f"Unknown provider '{provider}'. Choose: regex, ollama, bedrock, anthropic")
