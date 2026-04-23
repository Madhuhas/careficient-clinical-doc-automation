#!/bin/bash
# Start all 4 services and log to separate files

LOGDIR="$HOME/.careficient-logs"
mkdir -p "$LOGDIR"

echo "=== Starting Careficient services ==="

# Audio pipeline (port 8000)
cd "$(dirname "$0")/.."
PYTHONPATH=backend uvicorn audio_pipeline.app:app \
  --host 0.0.0.0 --port 8000 \
  > "$LOGDIR/audio.log" 2>&1 &
echo "Audio pipeline started (PID $!) — port 8000"

# OCR pipeline (port 8001)
PYTHONPATH=backend uvicorn ocr_pipeline.app:app \
  --host 0.0.0.0 --port 8001 \
  > "$LOGDIR/ocr.log" 2>&1 &
echo "OCR pipeline started (PID $!) — port 8001"

# OASIS prefill (port 8003)
PYTHONPATH=backend uvicorn oasis_prefill.app:app \
  --host 0.0.0.0 --port 8003 \
  > "$LOGDIR/oasis.log" 2>&1 &
echo "OASIS prefill started (PID $!) — port 8003"

# React UI (port 3000)
cd frontend/review-ui
npm start > "$LOGDIR/ui.log" 2>&1 &
echo "Review UI started (PID $!) — port 3000"

echo ""
echo "All services starting. Logs in $LOGDIR"
echo "  Audio:  tail -f $LOGDIR/audio.log"
echo "  OCR:    tail -f $LOGDIR/ocr.log"
echo "  OASIS:  tail -f $LOGDIR/oasis.log"
echo "  UI:     tail -f $LOGDIR/ui.log"
