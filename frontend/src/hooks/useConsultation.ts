import { useEffect } from 'react'
import { useConsultationStore } from '../context/ConsultationContext'
import type { TranscriptSegment, Consultation } from '../types/consultation'
import type { Patient } from '../types/patient'
import type { NormalizedSOAP } from '../context/ConsultationContext'

export function useConsultation(id?: string | number) {
  const store = useConsultationStore()

  useEffect(() => {
    if (id) {
      store.loadConsultation(id)
    }
  }, [id])

  const current = store.currentBundle

  const fallbackPatient: Patient = {
    id: id || '0',
    name: 'Loading patient...',
    age: null,
    gender: 'Unspecified',
    sex: 'Unspecified',
    mrn: '---',
    conditions: [],
    medications: [],
    allergies: [],
    complaint: '',
  }

  const fallbackConsultation: Consultation = {
    id: id || '0',
    patient_id: 0,
    status: 'draft',
    stage: 'idle',
    mode: 'live',
    audio_path: null,
    approved_by: null,
    approved_at: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }

  const fallbackNote: NormalizedSOAP = {
    subjective: '',
    objective: '',
    assessment: '',
    plan: '',
    Subjective: '',
    Objective: '',
    Assessment: '',
    Plan: '',
    approved: false,
  }

  return {
    consultation: current?.consultation ?? fallbackConsultation,
    currentPatient: current?.patient ?? fallbackPatient,
    transcript: current?.transcript ?? [],
    clinicalEntities: current?.clinicalEntities ?? [],
    note: current?.note ?? fallbackNote,
    safetySummary: current?.safetySummary ?? null,
    auditLogs: current?.auditLogs ?? [],
    approved: current?.approved ?? false,
    stage: current?.consultation.stage ?? 'idle',
    status: current?.consultation.status ?? 'draft',
    isLoading: store.isLoading,
    error: store.error,
    setTranscript: (segments: TranscriptSegment[]) => {
      if (id) store.updateTranscript(id, segments)
    },
    updateNote: (noteChanges: Partial<NormalizedSOAP>) => {
      if (id) return store.updateNote(id, noteChanges)
      return Promise.resolve(fallbackNote)
    },
    approve: () => {
      if (id) return store.approveConsultation(id)
      return Promise.resolve(false)
    },
    resolveAlert: (alertId: string | number, resolved = true) => {
      if (id) return store.resolveAlert(id, alertId, resolved)
      return Promise.resolve()
    },
    refresh: () => {
      if (id) return store.refreshConsultation(id)
      return Promise.resolve()
    },
    setStatus: (status: string) => {
      if (id) store.setStatus(id, status)
    },
  }
}
