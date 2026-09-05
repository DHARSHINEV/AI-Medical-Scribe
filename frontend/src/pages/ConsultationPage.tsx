import { useState } from 'react'
import { Check, Mic, ShieldCheck, Tag } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Notice, Panel } from '../components/layout/AppShell'
import { useConsultation } from '../hooks/useConsultation'
import { useRecording } from '../hooks/useRecording'
import { RecordingControls } from '../components/consultation/RecordingControls'
import { useConsultationProcessing } from '../hooks/useConsultationProcessing'

export default function ConsultationPage() {
  const { id = '' } = useParams()
  const c = useConsultation(id)
  const r = useRecording()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [activeTab, setActiveTab] = useState<'facts' | 'pipeline'>('facts')

  const p = useConsultationProcessing(
    c.consultation.id,
    (segments) => c.setTranscript?.(segments),
    (status) => c.setStatus(status === 'processing' ? 'processing' : status),
    () => c.refresh()
  )

  const startProcessing = () => {
    const audioPayload = selectedFile || r.audioBlob
    if (audioPayload) {
      p.process(audioPayload)
    }
  }

  const handleFileSelect = (file: File) => {
    setSelectedFile(file)
  }

  const hasAudioReady = !!r.audioBlob || !!selectedFile
  const genderDisplay = c.currentPatient.gender || c.currentPatient.sex || 'Unspecified'

  return (
    <>
      <Notice />
      <div className="workspace-head">
        <div>
          <span className="eyebrow">CONSULTATION WORKSPACE · #{c.consultation.id}</span>
          <h2>
            {c.currentPatient.name}{' '}
            <span className="patient-meta">
              {c.currentPatient.age != null ? `${c.currentPatient.age} yrs · ` : ''}
              {genderDisplay} · MRN: {c.currentPatient.mrn}
            </span>
          </h2>
          {c.currentPatient.complaint && <p>{c.currentPatient.complaint}</p>}
        </div>
        <div className="workspace-actions">
          <Link className="btn secondary" to={`/review/${c.consultation.id}`}>
            Open review
          </Link>
        </div>
      </div>

      {c.error && (
        <div className="form-error" style={{ marginBottom: '16px' }}>
          <b>Error loading consultation:</b> {c.error}
        </div>
      )}

      <div className="workspace-grid">
        {/* Left Panel: Historical Context */}
        <Panel title="Patient context" label="Historical record">
          <div className="context-block">
            <b>Active conditions</b>
            {(c.currentPatient.conditions || []).length > 0 ? (
              c.currentPatient.conditions.map((x) => <span key={x}>{x}</span>)
            ) : (
              <span className="muted">No known conditions</span>
            )}
          </div>
          <div className="context-block">
            <b>Medications</b>
            {(c.currentPatient.medications || []).length > 0 ? (
              c.currentPatient.medications.map((x) => <span key={x}>{x}</span>)
            ) : (
              <span className="muted">No current medications</span>
            )}
          </div>
          <div className="context-block alert-text">
            <b>Allergies & Alerts</b>
            {(c.currentPatient.allergies || []).length > 0 ? (
              c.currentPatient.allergies.map((x) => <span key={x}>⚠ {x}</span>)
            ) : (
              <span className="muted">NKDA</span>
            )}
          </div>
          <div className="context-block">
            <small style={{ color: 'var(--muted)', fontSize: '10px' }}>
              ℹ Historical context is preserved from EHR and kept distinct from current encounter observations.
            </small>
          </div>
        </Panel>

        {/* Center Panel: Real Transcript & Recording */}
        <Panel
          title="Consultation transcript"
          label={c.consultation.mode === 'demo' ? 'Demo fixture' : 'Live recording'}
        >
          <div className="recorder">
            <span className={`record-btn ${r.isRecording ? 'active' : ''}`}>
              <Mic size={18} />
            </span>
            <div>
              <b>
                {r.isRecording
                  ? r.isPaused
                    ? 'Recording paused'
                    : 'Recording encounter'
                  : hasAudioReady
                  ? 'Audio payload ready'
                  : 'Ready to record'}
              </b>
              <small>
                {r.error ??
                  (r.isRecording
                    ? 'Microphone active'
                    : selectedFile
                    ? `Selected file: ${selectedFile.name}`
                    : 'Capture audio via mic or select a test audio file')}
              </small>
            </div>
            <span className="timer">
              {String(Math.floor(r.duration / 60)).padStart(2, '0')}:
              {String(r.duration % 60).padStart(2, '0')}
            </span>
          </div>

          <RecordingControls
            recording={{
              ...r,
              onFileSelect: handleFileSelect,
              selectedFileName: selectedFile?.name,
              resetRecording: () => {
                r.resetRecording()
                setSelectedFile(null)
              },
            }}
          />

          {hasAudioReady && (
            <div style={{ padding: '0 14px 14px' }}>
              <button
                className="btn primary"
                onClick={startProcessing}
                disabled={p.step !== 'idle' && p.step !== 'error'}
              >
                {p.step === 'idle'
                  ? 'Process recording with AI'
                  : p.step === 'error'
                  ? 'Retry AI processing'
                  : 'Processing audio...'}
              </button>
            </div>
          )}

          <div className="transcript-list">
            {c.transcript.length === 0 && (
              <div style={{ padding: '24px 14px', color: 'var(--muted)', fontSize: '12px' }}>
                No transcript segments yet. Record or upload an encounter audio file and click &quot;Process recording with AI&quot;.
              </div>
            )}
            {c.transcript.map((s) => (
              <div className="transcript-line" id={`evidence-${s.id}`} key={s.id}>
                <time>{s.time}</time>
                <b className={`speaker ${s.speaker.toLowerCase() === 'patient' ? 'patient' : ''}`}>
                  {s.speaker}
                </b>
                <p>{s.text}</p>
              </div>
            ))}
          </div>

          <div style={{ padding: '8px 14px', borderTop: '1px solid var(--line)', background: '#fcfdfe' }}>
            <small style={{ color: 'var(--muted)', fontSize: '10px' }}>
              ℹ Speaker labeling is generated using heuristic two-speaker alternating diarization for assistive review, not voice-biometric acoustic diarization.
            </small>
          </div>
        </Panel>

        {/* Right Panel: AI Processing Pipeline & Clinical Entities */}
        <Panel title="Clinical AI extraction" label={p.step === 'idle' ? c.stage : p.step}>
          <div className="processing">
            <span className={p.step === 'uploading' || c.consultation.audio_path ? 'processing-active' : ''}>
              <Check size={14} /> Audio uploaded
            </span>
            <span className={p.step === 'transcribing' || c.transcript.length > 0 ? 'processing-active' : ''}>
              <Check size={14} /> Transcript structured
            </span>
            <span className={p.step === 'extracting' || c.clinicalEntities.length > 0 ? 'processing-active' : ''}>
              <Check size={14} /> Clinical facts extracted
            </span>
            <span className={p.step === 'safety_check' || c.safetySummary ? 'processing-active' : ''}>
              <Check size={14} /> Safety review ready
            </span>
          </div>

          {p.error && (
            <div className="form-error" style={{ margin: '14px' }}>
              <b>Pipeline Error:</b> {p.error}
            </div>
          )}

          <div className="tabs">
            <b
              onClick={() => setActiveTab('facts')}
              style={{ cursor: 'pointer', opacity: activeTab === 'facts' ? 1 : 0.6 }}
            >
              Extracted Facts ({c.clinicalEntities.length})
            </b>
            <span
              onClick={() => setActiveTab('pipeline')}
              style={{ cursor: 'pointer', opacity: activeTab === 'pipeline' ? 1 : 0.6, fontSize: '11px' }}
            >
              Safety Summary
            </span>
          </div>

          {activeTab === 'facts' && (
            <div style={{ maxHeight: '420px', overflowY: 'auto' }}>
              {c.clinicalEntities.length === 0 ? (
                <div style={{ padding: '16px', color: 'var(--muted)', fontSize: '11px' }}>
                  No entities extracted yet. Processing audio will populate symptoms, conditions, and findings.
                </div>
              ) : (
                c.clinicalEntities.map((ent) => (
                  <div className={`fact ${ent.type === 'allergy' ? 'warning' : ''}`} key={ent.id}>
                    <div className="fact-type">
                      {ent.type.toUpperCase()} · <Tag size={10} style={{ verticalAlign: 'middle' }} /> {ent.status}
                    </div>
                    <b>{ent.value}</b>
                    {ent.confidence != null && (
                      <p>Confidence: {Math.round(ent.confidence * 100)}%</p>
                    )}
                    {ent.evidence_segment_id != null && (
                      <a
                        onClick={() => {
                          const el = document.getElementById(`evidence-${ent.evidence_segment_id}`)
                          el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
                        }}
                      >
                        Evidence segment #{ent.evidence_segment_id}
                      </a>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'pipeline' && (
            <div style={{ padding: '14px', fontSize: '12px' }}>
              {c.safetySummary ? (
                <div>
                  <p>
                    <b>Total alerts:</b> {c.safetySummary.alert_count}
                  </p>
                  <p>
                    <b>High priority:</b> {c.safetySummary.high_priority_alert_count}
                  </p>
                  <p>
                    <b>Review required:</b> {c.safetySummary.review_required ? 'Yes' : 'No'}
                  </p>
                  <Link
                    to={`/review/${c.consultation.id}`}
                    className="btn primary"
                    style={{ marginTop: '12px', width: '100%' }}
                  >
                    Open Clinical Second Look
                  </Link>
                </div>
              ) : (
                <p className="muted">Safety validation will run upon AI processing.</p>
              )}
            </div>
          )}

          <div className="context-block">
            <b>
              <ShieldCheck size={15} /> Clinical Second Look
            </b>
            <span>Assistive verification only. Review evidence before approving the note.</span>
          </div>
        </Panel>
      </div>
    </>
  )
}
