export type ClinicalStatus = 'present' | 'absent' | 'uncertain' | 'historical' | string
export type ClinicalEntityType = 'symptom' | 'condition' | 'medication' | 'allergy' | 'finding' | string

export interface ClinicalEntity {
  id: number | string
  consultation_id?: number
  type: ClinicalEntityType
  label?: string | null
  value: string
  status: ClinicalStatus
  confidence?: number | null
  evidence_segment_id?: number | null
  evidenceSegmentId?: string | null
  created_at?: string
}
