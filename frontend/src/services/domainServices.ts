import { apiRequest, apiMultipart } from './api'
import type { Patient } from '../types/patient'
import type { Consultation, TranscriptSegment } from '../types/consultation'
import type { ClinicalEntity } from '../types/clinical'
import type { SOAPNote } from '../types/soap'
import type { SafetyAlert } from '../types/safety'

export const patientService = { getPatients: () => apiRequest<Patient[]>('/patients'), getPatient: (id:string) => apiRequest<Patient>(`/patients/${id}`), createPatient: (data: Partial<Patient>) => apiRequest<Patient>('/patients', {method:'POST', body:JSON.stringify(data)}) }
export const consultationService = { createConsultation: (data: Partial<Consultation>) => apiRequest<Consultation>('/consultations', {method:'POST',body:JSON.stringify(data)}), getConsultation: (id:string) => apiRequest<Consultation>(`/consultations/${id}`), getPatientHistory: (id:string) => apiRequest<Consultation[]>(`/patients/${id}/history`), approveConsultation: (id:string) => apiRequest<Consultation>(`/consultations/${id}/approve`, {method:'POST'}) }
export const transcriptionService = { uploadConsultationAudio: (id:string, blob:Blob) => { const form = new FormData(); form.append('audio', blob, 'consultation.webm'); return apiMultipart<{jobId:string}>(`/consultations/${id}/audio`, form) }, transcribeConsultation: (id:string) => apiRequest<TranscriptSegment[]>(`/consultations/${id}/transcribe`, {method:'POST'}), getTranscript: (id:string) => apiRequest<TranscriptSegment[]>(`/consultations/${id}/transcript`) }
export const clinicalService = { extractClinicalEntities: (id:string) => apiRequest<ClinicalEntity[]>(`/consultations/${id}/clinical-entities`, {method:'POST'}), generateSOAPNote: (id:string) => apiRequest<SOAPNote>(`/consultations/${id}/soap`, {method:'POST'}), updateSOAPNote: (id:string, note:SOAPNote) => apiRequest<SOAPNote>(`/consultations/${id}/soap`, {method:'PUT',body:JSON.stringify(note)}) }
export const safetyService = { validateConsultation: (id:string) => apiRequest<SafetyAlert[]>(`/consultations/${id}/validate`, {method:'POST'}), getSafetyAlerts: (id:string) => apiRequest<SafetyAlert[]>(`/consultations/${id}/safety-alerts`) }
export const authService = { login: (email:string, password:string) => apiRequest<{token:string}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})}) }
export const noteService = { generateSOAPNote: clinicalService.generateSOAPNote, updateSOAPNote: clinicalService.updateSOAPNote, approveConsultation: consultationService.approveConsultation }
