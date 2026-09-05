export type SafetySeverity = 'High' | 'Medium' | 'Low' | string

export interface SafetyAlert {
  id: number | string
  consultation_id?: number
  type?: string
  title: string
  detail: string
  severity: SafetySeverity
  evidence_segment_id?: number | null
  evidenceSegmentId?: string | null
  requires_review?: boolean
  resolved: boolean
  evidence_text?: string | null
  created_at?: string | null
}

export interface SafetySummary {
  consultation_id: number | string
  review_required: boolean
  alert_count: number
  high_priority_alert_count: number
  alerts: SafetyAlert[]
}
