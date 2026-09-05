import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { demoPatients, demoSegments, DEMO_CONSULTATION_ID } from '../data/demoData'
import type { Patient } from '../types/patient'
import type { Consultation, TranscriptSegment } from '../types/consultation'
import type { ClinicalEntity } from '../types/clinical'
import type { SOAPNote } from '../types/soap'
import type { SafetyAlert, SafetySummary } from '../types/safety'
import type { AuditLog } from '../types/audit'
import { consultationService, clinicalService, patientService, safetyService, transcriptionService } from '../services/domainServices'
import { useAuth } from './AuthContext'

export interface NormalizedSOAP {
  id?: number | string
  consultationId?: string
  subjective: string
  objective: string
  assessment: string
  plan: string
  Subjective: string
  Objective: string
  Assessment: string
  Plan: string
  approved: boolean
  updatedAt?: string
  updated_at?: string
}

export interface ConsultationBundle {
  consultation: Consultation
  patient: Patient
  transcript: TranscriptSegment[]
  clinicalEntities: ClinicalEntity[]
  note: NormalizedSOAP
  safetySummary: SafetySummary | null
  auditLogs: AuditLog[]
  approved: boolean
  mode: 'demo' | 'live'
}

interface ConsultationContextValue {
  activeConsultationId: string | number | null
  currentBundle: ConsultationBundle | null
  isLoading: boolean
  error: string | null
  loadConsultation: (id: string | number) => Promise<ConsultationBundle | null>
  createConsultation: (patientId: string | number) => Promise<string | number>
  createDemoConsultation: (patient?: Patient) => string
  updateTranscript: (id: string | number, segments: TranscriptSegment[]) => void
  updateNote: (id: string | number, noteChanges: Partial<NormalizedSOAP>) => Promise<NormalizedSOAP>
  approveConsultation: (id: string | number) => Promise<boolean>
  resolveAlert: (consultationId: string | number, alertId: string | number, resolved?: boolean) => Promise<void>
  refreshConsultation: (id: string | number) => Promise<void>
  setStatus: (id: string | number, status: string) => void
  demoConsultations: ConsultationBundle[]
}

const ConsultationContext = createContext<ConsultationContextValue | null>(null)

const DEFAULT_DEMO_NOTE: NormalizedSOAP = {
  subjective: 'Persistent dry cough for around 2 weeks. Denies fever, chills, or night sweats. Mild dyspnea on exertion.',
  objective: 'Lungs clear bilaterally. Current vitals not documented.',
  assessment: 'Persistent cough, unspecified. Suggestions require clinician verification.',
  plan: 'Hydration and throat lozenges. Verify medication dose before signing.',
  Subjective: 'Persistent dry cough for around 2 weeks. Denies fever, chills, or night sweats. Mild dyspnea on exertion.',
  Objective: 'Lungs clear bilaterally. Current vitals not documented.',
  Assessment: 'Persistent cough, unspecified. Suggestions require clinician verification.',
  Plan: 'Hydration and throat lozenges. Verify medication dose before signing.',
  approved: false,
}

function normalizeSOAP(raw?: Partial<SOAPNote> | null): NormalizedSOAP {
  const s = raw?.subjective || ''
  const o = raw?.objective || ''
  const a = raw?.assessment || ''
  const p = raw?.plan || ''
  return {
    id: raw?.id,
    consultationId: raw?.consultationId || (raw?.consultation_id ? String(raw.consultation_id) : undefined),
    subjective: s,
    objective: o,
    assessment: a,
    plan: p,
    Subjective: s,
    Objective: o,
    Assessment: a,
    Plan: p,
    approved: !!raw?.approved,
    updatedAt: raw?.updatedAt || raw?.updated_at || undefined,
    updated_at: raw?.updated_at || undefined,
  }
}

function createDemoBundle(patient = demoPatients[0], id = DEMO_CONSULTATION_ID): ConsultationBundle {
  return {
    consultation: {
      id,
      patient_id: patient.id,
      patientId: String(patient.id),
      status: 'review',
      stage: 'review',
      mode: 'demo',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    patient,
    transcript: demoSegments,
    clinicalEntities: [
      { id: 'ent-1', type: 'symptom', value: 'Persistent dry cough', status: 'present', confidence: 0.95 },
      { id: 'ent-2', type: 'condition', value: 'Hypertension', status: 'historical', confidence: 0.98 },
      { id: 'ent-3', type: 'allergy', value: 'Penicillin allergy', status: 'uncertain', confidence: 0.89 },
    ],
    note: { ...DEFAULT_DEMO_NOTE },
    safetySummary: {
      consultation_id: id,
      review_required: true,
      alert_count: 1,
      high_priority_alert_count: 1,
      alerts: [
        {
          id: 'demo-alert-1',
          consultation_id: Number(id) || 1,
          type: 'allergy_conflict',
          title: 'Allergy history discrepancy',
          detail: 'Patient record lists penicillin allergy; transcript includes uncertainty. Verify before prescribing.',
          severity: 'High',
          evidence_segment_id: 2,
          evidenceSegmentId: 'seg-2',
          requires_review: true,
          resolved: false,
        },
      ],
    },
    auditLogs: [
      {
        id: 'audit-demo-1',
        action: 'CONSULTATION_CREATED',
        created_at: new Date().toISOString(),
        details: { mode: 'demo' },
      },
    ],
    approved: false,
    mode: 'demo',
  }
}

export function ConsultationProvider({ children }: { children: ReactNode }) {
  const { mode } = useAuth()
  const [demoBundles, setDemoBundles] = useState<ConsultationBundle[]>([createDemoBundle()])
  const [currentBundle, setCurrentBundle] = useState<ConsultationBundle | null>(null)
  const [activeConsultationId, setActiveConsultationId] = useState<string | number | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Fetch real consultation bundle from backend in live mode
  const fetchLiveBundle = async (id: string | number): Promise<ConsultationBundle> => {
    const consultation = await consultationService.getConsultation(id)
    
    // Fetch patient
    let patient: Patient
    try {
      patient = await patientService.getPatient(consultation.patient_id)
    } catch {
      // Fallback empty patient structure if patient fetch fails
      patient = {
        id: consultation.patient_id,
        name: `Patient #${consultation.patient_id}`,
        mrn: `MRN-${consultation.patient_id}`,
        conditions: [],
        medications: [],
        allergies: [],
      }
    }

    // Fetch transcript
    let transcript: TranscriptSegment[] = []
    try {
      transcript = await transcriptionService.getTranscript(id)
    } catch {
      transcript = consultation.segments || []
    }

    // Fetch clinical entities
    let clinicalEntities: ClinicalEntity[] = []
    try {
      clinicalEntities = await clinicalService.getClinicalEntities(id)
    } catch {
      clinicalEntities = []
    }

    // Fetch SOAP note
    let note: NormalizedSOAP = normalizeSOAP(null)
    try {
      const rawNote = await clinicalService.getSOAPNote(id)
      note = normalizeSOAP(rawNote)
    } catch {
      // note might not be generated yet
      note = normalizeSOAP(null)
    }

    // Fetch safety summary
    let safetySummary: SafetySummary | null = null
    try {
      safetySummary = await safetyService.getSafetySummary(id)
    } catch {
      safetySummary = null
    }

    // Fetch audit logs
    let auditLogs: AuditLog[] = []
    try {
      auditLogs = await consultationService.getAuditLogs(id)
    } catch {
      auditLogs = []
    }

    const isApproved = consultation.status === 'approved' || consultation.stage === 'approved' || note.approved

    return {
      consultation,
      patient,
      transcript,
      clinicalEntities,
      note,
      safetySummary,
      auditLogs,
      approved: isApproved,
      mode: 'live',
    }
  }

  const loadConsultation = async (id: string | number): Promise<ConsultationBundle | null> => {
    setActiveConsultationId(id)
    setError(null)

    if (mode === 'demo' || String(id).startsWith('DEMO-')) {
      const found = demoBundles.find((b) => String(b.consultation.id) === String(id)) || demoBundles[0]
      setCurrentBundle(found)
      return found
    }

    setIsLoading(true)
    try {
      const bundle = await fetchLiveBundle(id)
      setCurrentBundle(bundle)
      return bundle
    } catch (err) {
      const msg = err instanceof Error ? err.message : `Failed to load consultation ${id}`
      setError(msg)
      return null
    } finally {
      setIsLoading(false)
    }
  }

  const refreshConsultation = async (id: string | number): Promise<void> => {
    if (mode === 'demo' || String(id).startsWith('DEMO-')) return
    try {
      const bundle = await fetchLiveBundle(id)
      setCurrentBundle(bundle)
    } catch {
      // ignore background refresh failure
    }
  }

  const createConsultation = async (patientId: string | number): Promise<string | number> => {
    if (mode === 'demo') {
      const patient = demoPatients.find((p) => String(p.id) === String(patientId)) || demoPatients[0]
      return createDemoConsultation(patient)
    }

    setIsLoading(true)
    setError(null)
    try {
      const created = await consultationService.createConsultation(patientId)
      setActiveConsultationId(created.id)
      const bundle = await fetchLiveBundle(created.id)
      setCurrentBundle(bundle)
      return created.id
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create consultation'
      setError(msg)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const createDemoConsultation = (patient = demoPatients[0]): string => {
    const id = `DEMO-${Date.now()}`
    const next = createDemoBundle(patient, id)
    setDemoBundles((prev) => [next, ...prev])
    setActiveConsultationId(id)
    setCurrentBundle(next)
    return id
  }

  const updateTranscript = (id: string | number, segments: TranscriptSegment[]) => {
    if (mode === 'demo' || String(id).startsWith('DEMO-')) {
      setDemoBundles((prev) =>
        prev.map((b) => (String(b.consultation.id) === String(id) ? { ...b, transcript: segments } : b))
      )
      setCurrentBundle((prev) => (prev && String(prev.consultation.id) === String(id) ? { ...prev, transcript: segments } : prev))
      return
    }

    // In live mode, update current local bundle
    setCurrentBundle((prev) => (prev && String(prev.consultation.id) === String(id) ? { ...prev, transcript: segments } : prev))
  }

  const updateNote = async (id: string | number, noteChanges: Partial<NormalizedSOAP>): Promise<NormalizedSOAP> => {
    if (mode === 'demo' || String(id).startsWith('DEMO-')) {
      const merged: NormalizedSOAP = normalizeSOAP({
        ...currentBundle?.note,
        ...noteChanges,
      })
      setDemoBundles((prev) =>
        prev.map((b) => (String(b.consultation.id) === String(id) ? { ...b, note: merged } : b))
      )
      setCurrentBundle((prev) => (prev && String(prev.consultation.id) === String(id) ? { ...prev, note: merged } : prev))
      return merged
    }

    // Save to real backend
    const payload: Partial<SOAPNote> = {
      subjective: noteChanges.subjective ?? noteChanges.Subjective,
      objective: noteChanges.objective ?? noteChanges.Objective,
      assessment: noteChanges.assessment ?? noteChanges.Assessment,
      plan: noteChanges.plan ?? noteChanges.Plan,
    }

    const saved = await clinicalService.updateSOAPNote(id, payload)
    const normalized = normalizeSOAP(saved)

    setCurrentBundle((prev) => {
      if (!prev || String(prev.consultation.id) !== String(id)) return prev
      return { ...prev, note: normalized }
    })

    return normalized
  }

  const approveConsultation = async (id: string | number): Promise<boolean> => {
    if (mode === 'demo' || String(id).startsWith('DEMO-')) {
      setDemoBundles((prev) =>
        prev.map((b) =>
          String(b.consultation.id) === String(id)
            ? {
                ...b,
                approved: true,
                consultation: { ...b.consultation, status: 'approved', stage: 'approved' },
                note: { ...b.note, approved: true },
              }
            : b
        )
      )
      setCurrentBundle((prev) =>
        prev && String(prev.consultation.id) === String(id)
          ? {
              ...prev,
              approved: true,
              consultation: { ...prev.consultation, status: 'approved', stage: 'approved' },
              note: { ...prev.note, approved: true },
            }
          : prev
      )
      return true
    }

    // Call real backend approve endpoint
    await consultationService.approveConsultation(id)
    // Refetch authoritative consultation state
    await refreshConsultation(id)
    return true
  }

  const resolveAlert = async (
    consultationId: string | number,
    alertId: string | number,
    resolved = true
  ): Promise<void> => {
    if (mode === 'demo' || String(consultationId).startsWith('DEMO-')) {
      setCurrentBundle((prev) => {
        if (!prev) return prev
        const updatedAlerts = (prev.safetySummary?.alerts || []).map((a) =>
          String(a.id) === String(alertId) ? { ...a, resolved } : a
        )
        const summary: SafetySummary = {
          ...prev.safetySummary!,
          alerts: updatedAlerts,
        }
        return { ...prev, safetySummary: summary }
      })
      return
    }

    // Call real backend
    if (resolved) {
      await safetyService.resolveAlert(consultationId, alertId, true)
    } else {
      await safetyService.unresolveAlert(consultationId, alertId)
    }
    // Refresh safety summary
    const summary = await safetyService.getSafetySummary(consultationId)
    setCurrentBundle((prev) => {
      if (!prev || String(prev.consultation.id) !== String(consultationId)) return prev
      return { ...prev, safetySummary: summary }
    })
  }

  const setStatus = (id: string | number, status: string) => {
    setCurrentBundle((prev) => {
      if (!prev || String(prev.consultation.id) !== String(id)) return prev
      return {
        ...prev,
        consultation: {
          ...prev.consultation,
          status,
          stage: status,
        },
      }
    })
  }

  const value = useMemo(
    () => ({
      activeConsultationId,
      currentBundle,
      isLoading,
      error,
      loadConsultation,
      createConsultation,
      createDemoConsultation,
      updateTranscript,
      updateNote,
      approveConsultation,
      resolveAlert,
      refreshConsultation,
      setStatus,
      demoConsultations: demoBundles,
    }),
    [activeConsultationId, currentBundle, isLoading, error, demoBundles]
  )

  return <ConsultationContext.Provider value={value}>{children}</ConsultationContext.Provider>
}

export function useConsultationStore() {
  const value = useContext(ConsultationContext)
  if (!value) throw new Error('useConsultationStore must be used inside ConsultationProvider')
  return value
}
