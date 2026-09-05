export interface Patient {
  id: number | string
  name: string
  age?: number | null
  gender?: string | null
  sex?: string
  mrn: string
  complaint?: string
  conditions: string[]
  medications: string[]
  allergies: string[]
  created_at?: string
  updated_at?: string
}
