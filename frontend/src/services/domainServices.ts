import { api, apiMultipart } from './api'
import type { Patient } from '../types/patient'
import type { Consultation, TranscriptSegment } from '../types/consultation'
import type { ClinicalEntity } from '../types/clinical'
import type { SOAPNote } from '../types/soap'
import type { SafetyAlert, SafetySummary } from '../types/safety'
import type { AuditLog } from '../types/audit'
import type { LabReport } from '../types/lab'


export const patientService = {
  getPatients: () => api.get<Patient[]>('/api/patients'),
  getPatient: (id: string | number) => api.get<Patient>(`/api/patients/${id}`),
  createPatient: (data: Partial<Patient>) => api.post<Patient>('/api/patients', data),
  updatePatient: (id: string | number, data: Partial<Patient>) => api.put<Patient>(`/api/patients/${id}`, data),
  deletePatient: (id: string | number) => api.delete<void>(`/api/patients/${id}`),
  getPatientHistory: (id: string | number) => api.get<Consultation[]>(`/api/patients/${id}/consultations`),
}

export const consultationService = {
  createConsultation: (patientId: string | number, doctorId?: number) =>
    api.post<Consultation>(`/api/patients/${patientId}/consultations`, { doctor_id: doctorId }),
  getConsultation: (id: string | number) => api.get<Consultation>(`/api/consultations/${id}`),
  getPatientConsultations: (patientId: string | number) =>
    api.get<Consultation[]>(`/api/patients/${patientId}/consultations`),
  approveConsultation: (id: string | number) =>
    api.post<{ id: number; status: string; stage: string; approved: boolean; approved_at: string; approved_by?: number }>(
      `/api/consultations/${id}/approve`,
      {}
    ),
  getAuditLogs: (id: string | number) => api.get<AuditLog[]>(`/api/consultations/${id}/audit`),
}

export const transcriptionService = {
  uploadConsultationAudio: (id: string | number, fileOrBlob: Blob | File) => {
    const form = new FormData()
    if (fileOrBlob instanceof File) {
      form.append('audio', fileOrBlob, fileOrBlob.name)
    } else {
      form.append('audio', fileOrBlob, 'consultation.webm')
    }
    return apiMultipart<{
      id: number
      patient_id: number
      patientId: string
      status: string
      stage: string
      audio_path: string
      jobId: string
    }>(`/api/consultations/${id}/audio`, form)
  },
  transcribeConsultation: (id: string | number) =>
    api.post<TranscriptSegment[]>(`/api/consultations/${id}/transcribe`, {}),
  getTranscript: (id: string | number) => api.get<TranscriptSegment[]>(`/api/consultations/${id}/transcript`),
}

export const clinicalService = {
  extractClinicalEntities: (id: string | number) =>
    api.post<ClinicalEntity[]>(`/api/consultations/${id}/extract`, {}),
  getClinicalEntities: (id: string | number) =>
    api.get<ClinicalEntity[]>(`/api/consultations/${id}/clinical_entities`),
  generateSOAPNote: (id: string | number) =>
    api.post<SOAPNote>(`/api/consultations/${id}/generate-note`, {}),
  getSOAPNote: (id: string | number) =>
    api.get<SOAPNote>(`/api/consultations/${id}/note`),
  updateSOAPNote: (id: string | number, note: Partial<SOAPNote>) =>
    api.put<SOAPNote>(`/api/consultations/${id}/note`, {
      subjective: note.subjective,
      objective: note.objective,
      assessment: note.assessment,
      plan: note.plan,
    }),
}

export const safetyService = {
  getSafetySummary: (id: string | number) =>
    api.get<SafetySummary>(`/api/consultations/${id}/safety`),
  validateConsultation: (id: string | number) =>
    api.post<SafetyAlert[]>(`/api/consultations/${id}/validate`, {}),
  getSafetyAlerts: (id: string | number) =>
    api.get<SafetyAlert[]>(`/api/consultations/${id}/alerts`),
  resolveAlert: (consultationId: string | number, alertId: string | number, resolved = true) =>
    api.post<SafetyAlert>(`/api/consultations/${consultationId}/safety/${alertId}/resolve`, { resolved }),
  unresolveAlert: (consultationId: string | number, alertId: string | number) =>
    api.post<SafetyAlert>(`/api/consultations/${consultationId}/safety/${alertId}/unresolve`, {}),
}

export const labService = {
  getLabs: (patientId?: string | number) => {
    const url = patientId ? `/api/labs?patient_id=${patientId}` : '/api/labs'
    return api.get<LabReport[]>(url)
  },
  getPatientLabs: (patientId: string | number) =>
    api.get<LabReport[]>(`/api/patients/${patientId}/labs`),
  uploadLabReport: (
    patientId: string | number,
    file: File,
    title?: string,
    consultationId?: string | number
  ) => {
    const form = new FormData()
    form.append('file', file)
    if (title) form.append('title', title)
    if (consultationId) form.append('consultation_id', String(consultationId))
    return apiMultipart<LabReport>(`/api/patients/${patientId}/labs`, form)
  },
  deleteLabReport: (id: string | number) => api.delete<void>(`/api/labs/${id}`),
  getLabDownloadUrl: (id: string | number) => `/api/labs/${id}/file`,
}

export const noteService = {
  getSOAPNote: clinicalService.getSOAPNote,
  generateSOAPNote: clinicalService.generateSOAPNote,
  updateSOAPNote: clinicalService.updateSOAPNote,
  approveConsultation: consultationService.approveConsultation,
}

