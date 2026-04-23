-- Postgres Schema for Careficient

CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE visits (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(id),
    visit_date DATE,
    source_type VARCHAR(20),  -- 'audio', 'ocr'
    raw_data JSONB,
    clinical_extract JSONB,
    oasis_prefill JSONB,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_at TIMESTAMP
);

CREATE INDEX idx_patient_visit ON visits(patient_id);
CREATE INDEX idx_reviewed ON visits(reviewed);

