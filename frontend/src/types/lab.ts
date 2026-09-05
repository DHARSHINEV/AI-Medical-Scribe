export interface LabReport {
  id: number
  patient_id: number
  consultation_id?: number | null
  title: string
  filename: string
  file_type: string
  file_size_bytes: number
  file_path: string
  uploaded_at: string
  patient_name?: string | null
  patient_mrn?: string | null
}
