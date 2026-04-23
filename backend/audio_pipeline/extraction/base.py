from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ClinicalExtractorBase(ABC):
    """Base class for all extraction providers (regex, ollama, bedrock, anthropic)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def extract_all(self, transcript: str):
        ...

    def extract_with_fallback(self, transcript: str, fallback=None):
        """Run extraction; fall back to another provider on any failure."""
        try:
            return self.extract_all(transcript)
        except Exception as exc:
            logger.warning(f"[{self.provider_name}] failed: {exc}. Falling back to regex.")
            if fallback:
                return fallback.extract_all(transcript)
            raise
