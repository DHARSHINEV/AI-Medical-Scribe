import { apiRequest } from './api'
import type { Consultation } from '../types/consultation'
export const consultationService = { get: (id: string) => apiRequest<Consultation>(`/consultations/${id}`), create: (patientId: string) => apiRequest<Consultation>('/patients/'+patientId+'/consultations', { method: 'POST', body: JSON.stringify({}) }) }
