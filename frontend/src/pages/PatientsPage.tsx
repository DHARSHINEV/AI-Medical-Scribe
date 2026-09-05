import { useEffect, useState } from 'react'
import { ChevronRight, Stethoscope } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageTitle } from '../components/layout/AppShell'
import { demoPatients } from '../data/demoData'
import { useAuth } from '../context/AuthContext'
import { patientService } from '../services/domainServices'
import type { Patient } from '../types/patient'

export default function PatientsPage() {
  const { mode } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (mode === 'demo') {
      setPatients(demoPatients)
      setLoading(false)
      return
    }

    let mounted = true
    setLoading(true)
    setError(null)

    patientService
      .getPatients()
      .then((data) => {
        if (mounted) {
          setPatients(data)
        }
      })
      .catch((err) => {
        if (mounted) {
          const msg = err instanceof Error ? err.message : 'Unable to load patients from backend.'
          setError(msg)
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [mode])

  return (
    <>
      <PageTitle eyebrow="PATIENT DIRECTORY" title="Patients">
        <Link className="btn primary" to="/consultations/new">
          <Stethoscope size={16} /> New consultation
        </Link>
      </PageTitle>

      {mode === 'demo' ? (
        <p className="muted">Demo records are synthetic and isolated from live clinical data.</p>
      ) : (
        <p className="muted">Authoritative patient records loaded from SQLite database.</p>
      )}

      {loading && <p className="muted" style={{ margin: '20px 0' }}>Loading patient records from server...</p>}

      {error && (
        <div className="form-error" style={{ margin: '20px 0' }}>
          <b>Error loading patients:</b> {error}
        </div>
      )}

      {!loading && !error && patients.length === 0 && (
        <div className="empty-card" style={{ marginTop: '20px' }}>
          <h3>No patients found</h3>
          <p>No patient records have been added to the database yet.</p>
        </div>
      )}

      <div className="patient-grid">
        {patients.map((p) => {
          const initials = p.name
            .split(' ')
            .map((n) => n[0])
            .join('')
            .slice(0, 2)
          const genderDisplay = p.gender || p.sex || 'Unspecified'
          const metaText = `${p.age != null ? `${p.age} · ` : ''}${genderDisplay} · ${p.mrn}`

          return (
            <Link to={`/patients/${p.id}`} className="patient-card" key={p.id}>
              <div className="patient-top">
                <span className="patient-avatar">{initials || 'PT'}</span>
                <ChevronRight size={16} />
              </div>
              <h3>{p.name}</h3>
              <span className="muted">{metaText}</span>
              {p.complaint && <p>{p.complaint}</p>}
              <div className="tag-row" style={{ marginTop: '10px' }}>
                {(p.conditions || []).map((c) => (
                  <span className="tag" key={c}>
                    {c}
                  </span>
                ))}
              </div>
            </Link>
          )
        })}
      </div>
    </>
  )
}
