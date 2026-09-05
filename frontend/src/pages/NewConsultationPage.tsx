import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { PageTitle } from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useConsultationStore } from '../context/ConsultationContext'
import { patientService } from '../services/domainServices'
import { demoPatients } from '../data/demoData'
import type { Patient } from '../types/patient'

export default function NewConsultationPage() {
  const [searchParams] = useSearchParams()
  const patientIdParam = searchParams.get('patient')
  const { mode } = useAuth()
  const navigate = useNavigate()
  const { createConsultation, createDemoConsultation } = useConsultationStore()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [patients, setPatients] = useState<Patient[]>([])

  useEffect(() => {
    const init = async () => {
      if (mode === 'demo') {
        const patient = demoPatients.find((p) => String(p.id) === patientIdParam) ?? demoPatients[0]
        const id = createDemoConsultation(patient)
        navigate(`/consultations/${id}`, { replace: true })
        return
      }

      try {
        if (patientIdParam) {
          const id = await createConsultation(patientIdParam)
          navigate(`/consultations/${id}`, { replace: true })
          return
        }

        // No patient in query param: fetch patients
        const list = await patientService.getPatients()
        setPatients(list)
        if (list.length > 0) {
          // Create consultation for the first patient automatically
          const id = await createConsultation(list[0].id)
          navigate(`/consultations/${id}`, { replace: true })
        } else {
          setLoading(false)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to create consultation')
        setLoading(false)
      }
    }

    init()
  }, [patientIdParam, mode, navigate])

  if (loading) {
    return (
      <div style={{ padding: '30px 0' }}>
        <p className="muted">Creating new clinical encounter...</p>
      </div>
    )
  }

  return (
    <>
      <PageTitle eyebrow="NEW CONSULTATION" title="Select Patient for Encounter" />
      {error && <div className="form-error" style={{ margin: '16px 0' }}>{error}</div>}

      {patients.length === 0 ? (
        <div className="empty-card">
          <h3>No patients available</h3>
          <p>Please register or add a patient before creating a consultation.</p>
          <Link to="/patients" className="btn primary" style={{ marginTop: '16px' }}>
            Go to Patients
          </Link>
        </div>
      ) : (
        <div className="patient-grid">
          {patients.map((p) => (
            <button
              key={p.id}
              className="patient-card"
              style={{ textAlign: 'left', cursor: 'pointer' }}
              onClick={async () => {
                setLoading(true)
                try {
                  const id = await createConsultation(p.id)
                  navigate(`/consultations/${id}`, { replace: true })
                } catch (err) {
                  setError(err instanceof Error ? err.message : 'Failed to create consultation')
                  setLoading(false)
                }
              }}
            >
              <h3>{p.name}</h3>
              <span className="muted">MRN: {p.mrn}</span>
              {p.complaint && <p>{p.complaint}</p>}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
