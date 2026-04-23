#!/usr/bin/env python
"""
Quick start script for audio pipeline development.
Handles dependency verification, environment setup, and server startup.
"""

import sys
import subprocess
import os
from pathlib import Path


def print_banner():
    """Print welcome banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║   CAREFICIENT CLINICAL AUDIO PIPELINE                        ║
    ║   Audio Transcription & Clinical Data Extraction             ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def verify_python_version():
    """Verify Python 3.8+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required (found {version.major}.{version.minor})")
        return False
    print(f"✓ Python {version.major}.{version.minor}")
    return True


def verify_ffmpeg():
    """Verify FFmpeg installation (optional)."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5
        )
        print("✓ FFmpeg installed")
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("⚠ FFmpeg not found (optional). Install with:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu: sudo apt-get install ffmpeg")
        print("   Windows: choco install ffmpeg")
        return True  # Don't fail if FFmpeg is missing


def setup_virtual_env():
    """Set up Python virtual environment (if needed)."""
    venv_path = Path(".venv")
    
    if venv_path.exists():
        print(f"✓ Virtual environment exists")
        return str(venv_path)
    
    print("Setting up virtual environment...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", ".venv"],
            check=True
        )
        print("✓ Virtual environment created")
        return str(venv_path)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return None


def install_dependencies():
    """Install Python dependencies."""
    print("\nInstalling dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=False
        )
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            timeout=300
        )
        print("✓ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if env_path.exists():
        print("✓ .env file exists")
        return True
    
    if env_example_path.exists():
        try:
            env_path.write_text(env_example_path.read_text())
            print("✓ .env file created from template")
            return True
        except Exception as e:
            print(f"⚠ Could not create .env file: {e}")
            return False
    
    return True


def start_server():
    """Start the FastAPI server."""
    print("\n" + "=" * 60)
    print("Starting Careficient Audio Pipeline...")
    print("=" * 60)
    print("\nAPI Documentation:")
    print("  - Swagger UI: http://localhost:8000/api/docs")
    print("  - ReDoc: http://localhost:8000/api/redoc")
    print("  - Health Check: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60 + "\n")
    
    try:
        subprocess.run(
            [
                sys.executable, "-m", "uvicorn",
                "app:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            check=False
        )
    except KeyboardInterrupt:
        print("\n✓ Server stopped")


def main():
    """Main entry point."""
    print_banner()
    
    # Verify environment
    print("\nVerifying environment...\n")
    checks = [
        ("Python version", verify_python_version),
        ("FFmpeg", verify_ffmpeg),
    ]
    
    for name, check in checks:
        if not check():
            print(f"\n❌ {name} check failed")
            sys.exit(1)
    
    # Setup
    print("\nSetting up environment...\n")
    
    if not create_env_file():
        print("⚠ Warning: Could not create .env file")
    
    # Check if requirements already installed
    try:
        import fastapi
        import whisper
        print("✓ Dependencies already installed")
    except ImportError:
        if not install_dependencies():
            sys.exit(1)
    
    # Start server
    start_server()


if __name__ == "__main__":
    main()
