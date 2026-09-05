export type SafetySeverity = 'High' | 'Medium' | 'Low'
export interface SafetyAlert { id: string; title: string; detail: string; severity: SafetySeverity; evidenceSegmentId?: string; resolved: boolean }
