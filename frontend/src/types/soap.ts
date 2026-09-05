export type SOAPSectionKey = 'subjective' | 'objective' | 'assessment' | 'plan'
export interface SOAPNote { id?: string; consultationId?: string; subjective: string; objective: string; assessment: string; plan: string; approved: boolean; updatedAt?: string }
