"""
Configuration and startup utilities for audio pipeline.
"""

import os
from typing import Optional
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Whisper
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    DEVICE: str = os.getenv("DEVICE", "auto")
    
    # Extraction provider
    # Options: regex | ollama | bedrock | anthropic
    # - regex     : deterministic patterns, always available (default)
    # - ollama    : local LLM via Ollama, set OLLAMA_MODEL + OLLAMA_BASE_URL
    # - bedrock   : AWS Bedrock, set BEDROCK_MODEL_ID + AWS credentials
    # - anthropic : Anthropic API, set ANTHROPIC_API_KEY
    EXTRACTOR_PROVIDER: str = os.getenv("EXTRACTOR_PROVIDER", "regex")

    # Ollama settings (used when EXTRACTOR_PROVIDER=ollama)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # Bedrock settings (used when EXTRACTOR_PROVIDER=bedrock)
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

    # Features
    EXTRACT_MEDICATIONS: bool = os.getenv("EXTRACT_MEDICATIONS", "true").lower() == "true"
    EXTRACT_VITALS: bool = os.getenv("EXTRACT_VITALS", "true").lower() == "true"
    EXTRACT_SYMPTOMS: bool = os.getenv("EXTRACT_SYMPTOMS", "true").lower() == "true"
    EXTRACT_ASSESSMENTS: bool = os.getenv("EXTRACT_ASSESSMENTS", "true").lower() == "true"
    
    # Storage (future)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", None)
    
    @classmethod
    def print_config(cls):
        """Print configuration."""
        print("=" * 50)
        print("Audio Pipeline Configuration")
        print("=" * 50)
        print(f"HOST: {cls.HOST}:{cls.PORT}")
        print(f"DEBUG: {cls.DEBUG}")
        print(f"LOG_LEVEL: {cls.LOG_LEVEL}")
        print(f"WHISPER_MODEL: {cls.WHISPER_MODEL}")
        print(f"DEVICE: {cls.DEVICE}")
        print(f"DATABASE_URL: {'Configured' if cls.DATABASE_URL else 'Not configured'}")
        print("=" * 50)


def verify_dependencies():
    """Verify required system dependencies."""
    import subprocess
    import sys
    
    dependencies = {
        "ffmpeg": "FFmpeg is required for audio processing",
        "pip": "pip is required to manage Python packages"
    }
    
    missing = []
    for cmd, msg in dependencies.items():
        try:
            subprocess.run([cmd, "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            missing.append(f"❌ {msg}")
    
    if missing:
        print("\nMissing Dependencies:")
        for item in missing:
            print(item)
        print("\nPlease install missing dependencies before continuing.")
        return False
    
    print("✓ All dependencies verified")
    return True


if __name__ == "__main__":
    Config.print_config()
    verify_dependencies()
