# High-Level Architecture

```
[Audio/PDF Upload] --> [FastAPI Gateway]
                          |
                          +--> [Whisper Audio Pipeline] --> [Clinical Extract]
                          |      (port 8000)
                          +--> [Tesseract OCR Pipeline] --> [Clinical Extract]
                                 (port 8001)
                                        |
                               [OASIS Prefill Mapper]
                                        |
                              [Review UI (React)]
                                        |
                                 [Postgres DB]
```

## Components
- **Ingestion**: Audio (Whisper), Docs (Tesseract)
- **Extraction**: Regex rules → Pydantic models
- **Prefill**: OASIS-E JSON templates
- **Review**: React editable UI
```

