import { useEffect, useState } from 'react'
import { ArrowRight, ClipboardCheck, FileText, Play, Stethoscope } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Notice, PageTitle, Panel } from '../components/layout/AppShell'
import { demoPatients, DEMO_CONSULTATION_ID } from '../data/demoData'
import { useAuth } from '../context/AuthContext'
import { useConsultationStore } from '../context/ConsultationContext'
import { patientService } from '../services/domainServices'
import type { Patient } from '../types/patient'
import type { Consultation } from '../types/consultation'

interface RecentRow {
  patient: Patient
  consultation?: Consultation
}

export default function DashboardPage() {
  const { mode } = useAuth()
  const navigate = useNavigate()
  const { demoConsultations, createDemoConsultation } = useConsultationStore()

  const [recentRows, setRecentRows] = useState<RecentRow[]>([])
  const [totalConsultations, setTotalConsultations] = useState(0)
  const [readyToApprove, setReadyToApprove] = useState(0)
  const [primaryConsultationId, setPrimaryConsultationId] = useState<string | number>(DEMO_CONSULTATION_ID)

  useEffect(() => {
    if (mode === 'demo') {
      const demoId = demoConsultations[0]?.consultation.id ?? DEMO_CONSULTATION_ID
      setPrimaryConsultationId(demoId)
      setTotalConsultations(demoConsultations.length)
      setReadyToApprove(demoConsultations.filter((b) => !b.approved).length)
      setRecentRows(
        demoPatients.map((p, i) => ({
          patient: p,
          consultation: i === 0 ? demoConsultations[0]?.consultation : undefined,
        }))
      )
      return
    }

    let mounted = true

    const loadLiveSnapshot = async () => {
      try {
        const patients = await patientService.getPatients()
        const historyPromises = patients.map((p) =>
          patientService.getPatientHistory(p.id).catch(() => [] as Consultation[])
        )
        const nested = await Promise.all(historyPromises)

        let allConsultations: { c: Consultation; p: Patient }[] = []
        nested.forEach((list, idx) => {
          list.forEach((c) => {
            allConsultations.push({ c, p: patients[idx] })
          })
        })

        allConsultations.sort(
          (a, b) => new Date(b.c.created_at || 0).getTime() - new Date(a.c.created_at || 0).getTime()
        )

        if (mounted) {
          setTotalConsultations(allConsultations.length)
          const unapprovedCount = allConsultations.filter(
            (item) => item.c.status === 'review'
          ).length
          setReadyToApprove(unapprovedCount)

          if (allConsultations.length > 0) {
            setPrimaryConsultationId(allConsultations[0].c.id)
            setRecentRows(
              allConsultations.slice(0, 5).map((item) => ({
                patient: item.p,
                consultation: item.c,
              }))
            )
          } else {
            setRecentRows(
              patients.slice(0, 5).map((p) => ({
                patient: p,
              }))
            )
          }
        }
      } catch {
        // fallback silent
      }
    }

    loadLiveSnapshot()

    return () => {
      mounted = false
    }
  }, [mode, demoConsultations])

  const handleStart = () => {
    if (mode === 'demo') {
      const id = createDemoConsultation()
      navigate(`/consultations/${id}`)
    } else {
      navigate('/consultations/new')
    }
  }

  const steps = [
    ['1', 'Capture encounter', `/consultations/${primaryConsultationId}`],
    ['2', 'Structure clinical facts', `/consultations/${primaryConsultationId}`],
    ['3', 'Second Look safety review', `/review/${primaryConsultationId}`],
    ['4', 'Clinician approves note', `/review/${primaryConsultationId}`],
    ['5', 'Prepare prescription', `/prescription/${primaryConsultationId}`],
  ]

  return (
    <>
      <Notice />
      <div className="hero-row">
        <div className="hero-card">
          <span className="label">TODAY&apos;S WORKSPACE</span>
          <h2>
            Turn a conversation into a<br />
            <em>reviewable clinical note.</em>
          </h2>
          <p>
            Capture the encounter, surface documentation gaps, and keep the clinician in control from
            transcript to signed note.
          </p>
          <div className="actions">
            <button className="btn primary" onClick={handleStart}>
              <Play size={16} /> {mode === 'demo' ? 'Start demo consultation' : 'New consultation'}{' '}
              <ArrowRight size={15} />
            </button>
            <Link className="btn secondary" to="/patients">
              <Stethoscope size={16} /> Choose patient
            </Link>
          </div>
        </div>

        <Panel title="THE WORKFLOW" label="5 steps">
          <div className="workflow-list">
            {steps.map(([n, label, to]) => (
              <Link className="flow-step" to={to} key={n}>
                <span>{n}</span>
                <b>{label}</b>
                <ArrowRight size={14} />
              </Link>
            ))}
          </div>
        </Panel>
      </div>

      <PageTitle eyebrow="CLINIC SNAPSHOT" title="Today at a glance" />
      <div className="metric-grid">
        <div className="metric">
          <div className="metric-icon">
            <FileText size={18} />
          </div>
          <b>{totalConsultations}</b>
          <span>Consultations</span>
          <small>{mode === 'demo' ? 'In demo workspace' : 'In SQLite database'}</small>
        </div>
        <div className="metric">
          <div className="metric-icon warn">
            <ClipboardCheck size={18} />
          </div>
          <b>{readyToApprove}</b>
          <span>Awaiting review</span>
          <small>Second Look active</small>
        </div>
        <div className="metric">
          <div className="metric-icon good">
            <Stethoscope size={18} />
          </div>
          <b>{mode === 'demo' ? demoPatients.length : recentRows.length}</b>
          <span>Active patients</span>
          <small>{mode === 'demo' ? 'Synthetic records' : 'Clinical records'}</small>
        </div>
      </div>

      <PageTitle eyebrow="RECENT ENCOUNTERS" title="Continue where you left off" />
      <div className="table-card">
        {recentRows.length === 0 ? (
          <div style={{ padding: '24px', color: 'var(--muted)', textAlign: 'center' }}>
            No recent encounters found. Choose a patient or start a new consultation.
          </div>
        ) : (
          recentRows.map(({ patient: p, consultation: c }) => {
            const dest = c ? `/consultations/${c.id}` : `/patients/${p.id}`
            const statusLabel = c
              ? c.status === 'approved'
                ? 'Approved'
                : c.status === 'review'
                ? 'Review'
                : 'Draft'
              : 'Registered'
            const badgeClass =
              statusLabel === 'Approved' ? 'approved' : statusLabel === 'Review' ? 'reviewed' : 'draft'

            return (
              <Link className="table-row" to={dest} key={c ? `${p.id}-${c.id}` : p.id}>
                <span>
                  <b>{p.name}</b>
                  <small>
                    MRN: {p.mrn} {p.age != null ? `· ${p.age} yrs` : ''}
                  </small>
                </span>
                <span>{p.complaint || (c ? `Stage: ${c.stage}` : 'Regular checkup')}</span>
                <span className={`badge ${badgeClass}`}>{statusLabel}</span>
                <ArrowRight size={16} />
              </Link>
            )
          })
        )}
      </div>
    </>
  )
}
