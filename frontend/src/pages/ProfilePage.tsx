import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowRight, FileText, Plus, Stethoscope } from 'lucide-react'
import { PageTitle, Panel } from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useConsultationStore } from '../context/ConsultationContext'
import { patientService } from '../services/domainServices'
import { demoPatients } from '../data/demoData'
import type { Patient } from '../types/patient'
import type { Consultation } from '../types/consultation'

export default function ProfilePage() {
  const { patientId = '' } = useParams()
  const { mode } = useAuth()
  const navigate = useNavigate()
  const { createConsultation, createDemoConsultation } = useConsultationStore()

  const [patient, setPatient] = useState<Patient | null>(null)
  const [history, setHistory] = useState<Consultation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  useEffect(() => {
    if (mode === 'demo' || patientId.startsWith('DEMO-')) {
      const demo = demoPatients.find((p) => String(p.id) === patientId) || demoPatients[0]
      setPatient(demo)
      setLoading(false)
      return
    }

    let mounted = true
    setLoading(true)
    setError(null)

    Promise.all([
      patientService.getPatient(patientId),
      patientService.getPatientHistory(patientId).catch(() => [] as Consultation[]),
    ])
      .then(([pData, histData]) => {
        if (mounted) {
          setPatient(pData)
          setHistory(histData)
        }
      })
      .catch((err) => {
        if (mounted) {
          const msg = err instanceof Error ? err.message : 'Unable to load patient profile.'
          setError(msg)
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [patientId, mode])

  const handleStartEncounter = async () => {
    if (!patient) return
    setStarting(true)
    try {
      if (mode === 'demo' || String(patient.id).startsWith('DEMO-')) {
        const id = createDemoConsultation(patient)
        navigate(`/consultations/${id}`)
      } else {
        const id = await createConsultation(patient.id)
        navigate(`/consultations/${id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create consultation')
      setStarting(false)
    }
  }

  if (loading) {
    return <p className="muted" style={{ margin: '30px 0' }}>Loading patient profile...</p>
  }

  if (error && !patient) {
    return (
      <div className="form-error" style={{ margin: '30px 0' }}>
        <b>Error loading patient:</b> {error}
      </div>
    )
  }

  if (!patient) {
    return <p className="muted" style={{ margin: '30px 0' }}>Patient not found.</p>
  }

  const genderDisplay = patient.gender || patient.sex || 'Unspecified'

  return (
    <>
      <PageTitle
        eyebrow={mode === 'demo' ? 'PATIENT PROFILE · SYNTHETIC' : 'PATIENT PROFILE · CLINICAL RECORD'}
        title={patient.name}
      >
        <button className="btn primary" onClick={handleStartEncounter} disabled={starting}>
          <Stethoscope size={16} /> {starting ? 'Creating encounter...' : 'Start encounter'}
        </button>
      </PageTitle>

      {error && <div className="form-error" style={{ marginBottom: '16px' }}>{error}</div>}

      <div className="profile-grid">
        <div className="info-card">
          <b>Demographics</b>
          <p>
            {patient.age != null ? `${patient.age} yrs · ` : ''}
            {genderDisplay} · MRN: {patient.mrn}
          </p>
          {patient.complaint && <p style={{ marginTop: '8px' }}>{patient.complaint}</p>}
        </div>

        <div className="info-card">
          <b>Conditions & medications</b>
          {(patient.conditions || []).length > 0 ? (
            patient.conditions.map((x) => (
              <p key={x} className="list-line">
                <span className="blue-dot" /> {x}
              </p>
            ))
          ) : (
            <p className="muted">No documented chronic conditions</p>
          )}

          {(patient.medications || []).length > 0 ? (
            patient.medications.map((x) => (
              <p key={x} className="list-line">
                <span className="blue-dot" /> {x}
              </p>
            ))
          ) : (
            <p className="muted">No current medications</p>
          )}
        </div>

        <div className="info-card warning">
          <b>Allergies & Contraindications</b>
          {(patient.allergies || []).length > 0 ? (
            patient.allergies.map((x) => (
              <p key={x} style={{ color: 'var(--red)', fontWeight: 600, marginTop: '4px' }}>
                ⚠ {x}
              </p>
            ))
          ) : (
            <p className="muted">No known drug allergies (NKDA)</p>
          )}
        </div>
      </div>

      {history.length > 0 && (
        <Panel title="Previous Consultations" label={`${history.length} records`}>
          <div className="table-card">
            {history.map((c) => (
              <Link className="table-row" to={`/consultations/${c.id}`} key={c.id}>
                <span>
                  <b>Consultation #{c.id}</b>
                  <small>{c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recent'}</small>
                </span>
                <span>Stage: {c.stage}</span>
                <span className={`badge ${c.status === 'approved' ? 'approved' : 'draft'}`}>
                  {c.status.toUpperCase()}
                </span>
                <FileText size={16} />
                <ArrowRight size={16} />
              </Link>
            ))}
          </div>
        </Panel>
      )}
    </>
  )
}
