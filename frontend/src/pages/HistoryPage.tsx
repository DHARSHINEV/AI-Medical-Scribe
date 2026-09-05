import { useEffect, useState } from 'react'
import { ArrowRight, FileText, Stethoscope } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageTitle, Panel } from '../components/layout/AppShell'
import { useAuth } from '../context/AuthContext'
import { useConsultationStore } from '../context/ConsultationContext'
import { patientService } from '../services/domainServices'
import type { Consultation } from '../types/consultation'
import type { Patient } from '../types/patient'

interface HistoryItem {
  consultation: Consultation
  patient?: Patient
}

export default function HistoryPage() {
  const { mode } = useAuth()
  const { demoConsultations } = useConsultationStore()
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (mode === 'demo') {
      const demoItems: HistoryItem[] = demoConsultations.map((b) => ({
        consultation: b.consultation,
        patient: b.patient,
      }))
      setItems(demoItems)
      setLoading(false)
      return
    }

    let mounted = true
    setLoading(true)
    setError(null)

    const fetchAllHistory = async () => {
      try {
        const patients = await patientService.getPatients()
        const patientMap = new Map<number | string, Patient>()
        patients.forEach((p) => patientMap.set(p.id, p))

        const historyPromises = patients.map((p) =>
          patientService.getPatientHistory(p.id).catch(() => [] as Consultation[])
        )
        const nestedConsultations = await Promise.all(historyPromises)

        const flattened: HistoryItem[] = []
        nestedConsultations.forEach((conList, idx) => {
          const patient = patients[idx]
          conList.forEach((c) => {
            flattened.push({
              consultation: c,
              patient,
            })
          })
        })

        // Sort descending by id or created_at
        flattened.sort((a, b) => {
          const dateA = new Date(a.consultation.created_at || 0).getTime()
          const dateB = new Date(b.consultation.created_at || 0).getTime()
          return dateB - dateA
        })

        if (mounted) {
          setItems(flattened)
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : 'Unable to load consultation history')
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    fetchAllHistory()

    return () => {
      mounted = false
    }
  }, [mode, demoConsultations])

  return (
    <>
      <PageTitle eyebrow="CONSULTATION LOG" title="History">
        <span className={`status-pill ${mode === 'live' ? 'connected' : ''}`}>
          <i /> {mode === 'demo' ? 'Synthetic Demo Workspace' : 'Live Database Log'}
        </span>
      </PageTitle>

      {loading && <p className="muted" style={{ margin: '20px 0' }}>Loading consultation records...</p>}

      {error && (
        <div className="form-error" style={{ margin: '20px 0' }}>
          <b>Error loading history:</b> {error}
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="empty-card" style={{ marginTop: '20px' }}>
          <h3>No consultations found</h3>
          <p>No encounters have been recorded yet. Start a new consultation to begin.</p>
          <Link to="/consultations/new" className="btn primary" style={{ marginTop: '16px' }}>
            <Stethoscope size={15} /> Start New Consultation
          </Link>
        </div>
      )}

      {items.length > 0 && (
        <Panel title="Consultation records" label={`${items.length} records`}>
          <div className="table-card">
            {items.map(({ consultation: c, patient: p }) => {
              const patientName = p?.name || `Patient #${c.patient_id}`
              const complaintText = p?.complaint || `Stage: ${c.stage}`
              const isApproved = c.status === 'approved' || c.stage === 'approved'

              let badgeClass = 'draft'
              if (isApproved) badgeClass = 'approved'
              else if (c.status === 'review' || c.stage === 'review') badgeClass = 'reviewed'
              else if (c.status === 'failed' || c.stage === 'error') badgeClass = 'high'

              const statusLabel = isApproved
                ? 'Approved'
                : c.status === 'review'
                ? 'Ready for Review'
                : c.status.toUpperCase()

              return (
                <Link className="table-row" to={`/review/${c.id}`} key={c.id}>
                  <span>
                    <b>{patientName}</b>
                    <small>
                      Encounter #{c.id} · {c.created_at ? new Date(c.created_at).toLocaleDateString() : 'Recent'}
                    </small>
                  </span>
                  <span>{complaintText}</span>
                  <span className={`badge ${badgeClass}`}>{statusLabel}</span>
                  <FileText size={16} />
                  <ArrowRight size={16} />
                </Link>
              )
            })}
          </div>
        </Panel>
      )}
    </>
  )
}
