export interface AuditLog {
  id: number | string
  action: string
  user_id?: number | null
  consultation_id?: number | null
  details?: Record<string, unknown> | null
  created_at: string
}
