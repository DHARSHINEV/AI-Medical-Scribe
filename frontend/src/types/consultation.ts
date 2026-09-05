export type Speaker = 'Doctor' | 'Patient' | 'Unassigned'
export type ConsultationStatus = 'draft' | 'processing' | 'review' | 'approved'
export type ConsultationStage = 'idle' | 'recording' | 'uploading' | 'transcribing' | 'extracting' | 'generating' | 'safety_check' | 'review' | 'approved' | 'error'
export interface TranscriptSegment { id: string; time: string; speaker: Speaker; text: string; startTime?: number; endTime?: number; confidence?: number }
export interface Consultation { id: string; patientId: string; status: ConsultationStatus; stage: ConsultationStage; createdAt?: string; updatedAt?: string; segments?: TranscriptSegment[] }
