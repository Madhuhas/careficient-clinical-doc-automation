FROM python:3.10-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .  # Note: create top-level requirements later
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

EXPOSE 8000 8001

CMD ["sh", "-c", "uvicorn audio_pipeline.app:app --host 0.0.0.0 --port 8000 & uvicorn ocr_pipeline.app:app --host 0.0.0.0 --port 8001"]

