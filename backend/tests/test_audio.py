import pytest
from audio_pipeline.extractor import ClinicalExtractor

def test_vitals_extraction():
    extractor = ClinicalExtractor()
    transcript = \"BP 120/80, HR 72 bpm\"
    extract = extractor.extract_all(transcript)
    assert len(extract.vitals) >= 2

# Add more tests
```

