import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API = {
  audio: process.env.REACT_APP_AUDIO_URL || 'http://localhost:8000',
  ocr:   process.env.REACT_APP_OCR_URL   || 'http://localhost:8001',
  oasis: process.env.REACT_APP_OASIS_URL || 'http://localhost:8003',
};

function StatusBadge({ status }) {
  const colors = { healthy: '#2e7d32', error: '#c62828', loading: '#1565c0' };
  return (
    <span style={{
      background: colors[status] || '#555',
      color: '#fff',
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 12,
      marginLeft: 8,
    }}>
      {status}
    </span>
  );
}

function AudioPanel() {
  const [audioFile, setAudioFile] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [oasis, setOasis] = useState(null);
  const [step, setStep] = useState('idle');
  const [error, setError] = useState(null);
  const [patientId, setPatientId] = useState('P001');
  const [visitDate, setVisitDate] = useState(new Date().toISOString().slice(0, 10));

  const run = async () => {
    if (!audioFile) return setError('Please select an audio file.');
    setError(null);
    setTranscript(null);
    setExtraction(null);
    setOasis(null);

    try {
      setStep('transcribing');
      const form = new FormData();
      form.append('audio', audioFile);
      form.append('patient_id', patientId);
      form.append('visit_date', visitDate);
      const t = await axios.post(`${API.audio}/transcribe`, form);
      setTranscript(t.data);

      setStep('extracting');
      const e = await axios.post(`${API.audio}/extract`, { transcript_id: t.data.transcript_id });
      setExtraction(e.data);

      setStep('prefill');
      const o = await axios.post(`${API.audio}/oasis-prefill`, {
        transcript_id: t.data.transcript_id,
        patient_id: patientId,
        visit_date: visitDate,
      });
      setOasis(o.data);
      setStep('done');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setError(`Error: ${msg}`);
      setStep('idle');
    }
  };

  const labels = {
    idle: 'Run Audio Pipeline',
    transcribing: 'Transcribing…',
    extracting: 'Extracting…',
    prefill: 'Generating OASIS…',
    done: 'Run Again',
  };

  return (
    <div className="panel">
      <h2>Audio Pipeline</h2>
      <div className="form-row">
        <label>Audio file</label>
        <input type="file" accept="audio/*" onChange={e => setAudioFile(e.target.files[0])} />
      </div>
      <div className="form-row">
        <label>Patient ID</label>
        <input value={patientId} onChange={e => setPatientId(e.target.value)} className="short" />
      </div>
      <div className="form-row">
        <label>Visit Date</label>
        <input type="date" value={visitDate} onChange={e => setVisitDate(e.target.value)} className="short" />
      </div>
      <button onClick={run} disabled={step !== 'idle' && step !== 'done'}>
        {labels[step]}
      </button>
      {error && <div className="error">{error}</div>}

      {transcript && (
        <section>
          <h3>Transcript <StatusBadge status="healthy" /></h3>
          <p className="transcript-text">{transcript.transcript}</p>
          <small>Duration: {transcript.duration_seconds?.toFixed(1)}s · Language: {transcript.language}</small>
        </section>
      )}

      {extraction && (
        <section>
          <h3>Clinical Extraction <StatusBadge status="healthy" /></h3>
          <VitalsEditor vitals={extraction.clinical_extract?.vitals ?? []} />
          <h4>Medications</h4>
          <DataTable rows={extraction.clinical_extract?.medications ?? []} fields={['name', 'dose', 'frequency', 'route']} />
          <h4>Symptoms</h4>
          <DataTable rows={extraction.clinical_extract?.symptoms ?? []} fields={['symptom', 'location', 'severity']} />
        </section>
      )}

      {oasis && (
        <section>
          <h3>OASIS Prefill <StatusBadge status="healthy" /></h3>
          <pre>{JSON.stringify(oasis, null, 2)}</pre>
        </section>
      )}
    </div>
  );
}

function OcrPanel() {
  const [docFile, setDocFile] = useState(null);
  const [ocrResult, setOcrResult] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [step, setStep] = useState('idle');
  const [error, setError] = useState(null);

  const run = async () => {
    if (!docFile) return setError('Please select a document file.');
    setError(null);
    setOcrResult(null);
    setExtraction(null);

    try {
      setStep('ocr');
      const form = new FormData();
      form.append('document', docFile);
      const o = await axios.post(`${API.ocr}/ocr`, form);
      setOcrResult(o.data);

      setStep('extracting');
      const e = await axios.post(`${API.ocr}/extract`, { document_id: o.data.document_id });
      setExtraction(e.data);
      setStep('done');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setError(`Error: ${msg}`);
      setStep('idle');
    }
  };

  const labels = {
    idle: 'Run OCR Pipeline',
    ocr: 'Running OCR…',
    extracting: 'Extracting…',
    done: 'Run Again',
  };

  return (
    <div className="panel">
      <h2>OCR Pipeline</h2>
      <div className="form-row">
        <label>Document (PDF / JPG / PNG / TIFF)</label>
        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff,.tif" onChange={e => setDocFile(e.target.files[0])} />
      </div>
      <button onClick={run} disabled={step !== 'idle' && step !== 'done'}>
        {labels[step]}
      </button>
      {error && <div className="error">{error}</div>}

      {ocrResult && (
        <section>
          <h3>OCR Result <StatusBadge status="healthy" /></h3>
          <small>Pages: {ocrResult.total_pages} · Confidence: {(ocrResult.overall_confidence * 100).toFixed(0)}%</small>
          <pre>{ocrResult.full_text?.slice(0, 600)}{ocrResult.full_text?.length > 600 ? '…' : ''}</pre>
        </section>
      )}

      {extraction && (
        <section>
          <h3>Clinical Extraction <StatusBadge status="healthy" /></h3>
          <VitalsEditor vitals={extraction.clinical_extract?.vitals ?? []} />
          <h4>Medications</h4>
          <DataTable rows={extraction.clinical_extract?.medications ?? []} fields={['name', 'dose', 'frequency', 'route']} />
        </section>
      )}
    </div>
  );
}

function VitalsEditor({ vitals }) {
  const [local, setLocal] = useState(vitals);

  const update = (i, val) =>
    setLocal(prev => prev.map((v, idx) => idx === i ? { ...v, value: val } : v));

  if (!local.length) return <p style={{ color: '#888' }}>No vitals extracted.</p>;
  return (
    <>
      <h4>Vitals</h4>
      <table className="vitals-table">
        <thead><tr><th>Name</th><th>Value</th><th>Unit</th><th>Confidence</th></tr></thead>
        <tbody>
          {local.map((v, i) => (
            <tr key={i}>
              <td>{v.name}</td>
              <td>
                <input
                  value={v.value ?? ''}
                  onChange={e => update(i, e.target.value)}
                  className="short"
                />
              </td>
              <td>{v.unit ?? '—'}</td>
              <td>{v.confidence != null ? `${(v.confidence * 100).toFixed(0)}%` : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function DataTable({ rows, fields }) {
  if (!rows.length) return <p style={{ color: '#888' }}>None extracted.</p>;
  return (
    <table className="vitals-table">
      <thead>
        <tr>{fields.map(f => <th key={f}>{f}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            {fields.map(f => <td key={f}>{row[f] ?? '—'}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function HealthBar() {
  const [health, setHealth] = useState({});

  React.useEffect(() => {
    const check = async () => {
      const results = {};
      for (const [name, url] of Object.entries(API)) {
        try {
          await axios.get(`${url}/health`, { timeout: 3000 });
          results[name] = 'healthy';
        } catch {
          results[name] = 'error';
        }
      }
      setHealth(results);
    };
    check();
  }, []);

  return (
    <div className="health-bar">
      {Object.entries(API).map(([name, url]) => (
        <span key={name}>
          {name} ({url}) <StatusBadge status={health[name] ?? 'loading'} />
        </span>
      ))}
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState('audio');

  return (
    <div className="App">
      <h1>Careficient Clinical Doc Automation</h1>
      <HealthBar />
      <div className="tabs">
        <button className={tab === 'audio' ? 'active' : ''} onClick={() => setTab('audio')}>Audio</button>
        <button className={tab === 'ocr' ? 'active' : ''} onClick={() => setTab('ocr')}>OCR</button>
      </div>
      {tab === 'audio' && <AudioPanel />}
      {tab === 'ocr' && <OcrPanel />}
    </div>
  );
}
