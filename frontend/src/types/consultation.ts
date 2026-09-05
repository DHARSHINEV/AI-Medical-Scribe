export type Speaker = 'Doctor' | 'Patient' | 'Unassigned' | string
export type ConsultationStatus = 'draft' | 'processing' | 'review' | 'approved' | 'failed' | 'error' | string
export type ConsultationStage = 'idle' | 'recording' | 'uploading' | 'uploaded' | 'transcribing' | 'extracting' | 'generating' | 'safety_check' | 'review' | 'approved' | 'failed' | 'error' | string

export interface TranscriptSegment {
  id: number | string
  consultation_id?: number
  time: string
  speaker: Speaker
  text: string
  start_time?: number
  end_time?: number
  startTime?: number
  endTime?: number
  confidence?: number | null
}

export interface Consultation {
  id: number | string
  patient_id: number | string
  patientId?: string
  doctor_id?: number | null
  status: ConsultationStatus
  stage: ConsultationStage
  audio_path?: string | null
  approved_by?: number | null
  approved_at?: string | null
  created_at?: string
  updated_at?: string
  createdAt?: string
  updatedAt?: string
  segments?: TranscriptSegment[]
  mode?: 'demo' | 'live'
}
