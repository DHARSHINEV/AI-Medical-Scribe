export type SOAPSectionKey = 'subjective' | 'objective' | 'assessment' | 'plan'

export interface SOAPNote {
  id?: number | string
  consultation_id?: number | string
  consultationId?: string
  subjective: string
  objective: string
  assessment: string
  plan: string
  approved: boolean
  approved_by?: number | null
  approved_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  updatedAt?: string | null
}
