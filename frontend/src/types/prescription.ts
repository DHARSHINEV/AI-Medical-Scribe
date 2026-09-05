export interface MedicationItem { id: string; name: string; strength: string; dose: string; route: string; frequency: string; duration: string; quantity: string; instructions: string }
export interface Prescription { id: string; consultationId: string; status: 'draft' | 'finalized'; medications: MedicationItem[]; advice: string; followUp: string; clinicianNotes: string }
