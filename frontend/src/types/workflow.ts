export interface WorkflowStep { id: string; label: string; to: string; complete?: boolean }
export interface EvidenceReference { evidenceSegmentId?: string; alertId: string; label: string }
