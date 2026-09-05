export type ClinicalStatus = 'present' | 'absent' | 'uncertain' | 'historical'
export type ClinicalEntityType = 'symptom' | 'condition' | 'medication' | 'allergy' | 'finding'
export interface ClinicalEntity { id: string; type: ClinicalEntityType; label?: string; value: string; status: ClinicalStatus; confidence?: number; evidenceSegmentId?: string }
