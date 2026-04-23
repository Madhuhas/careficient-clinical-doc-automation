#!/bin/bash
set -e

echo "=== Installing system dependencies ==="
sudo apt-get update -qq
sudo apt-get install -y -qq tesseract-ocr poppler-utils ffmpeg

echo "=== Installing Python dependencies ==="

# Audio pipeline — CPU-only torch to keep size manageable
pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
pip install --quiet -r backend/audio_pipeline/requirements.txt

# OCR pipeline
pip install --quiet -r backend/ocr_pipeline/requirements.txt

# OASIS prefill
pip install --quiet -r backend/oasis_prefill/requirements.txt

echo "=== Installing frontend dependencies ==="
cd frontend/review-ui
npm install --silent
cd -

echo "=== Setup complete ==="
