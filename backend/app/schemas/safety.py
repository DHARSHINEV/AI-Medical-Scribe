from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.transcript import TranscriptSegmentResponse


class SafetyAlertBase(BaseModel):
    type: str
    title: str
    detail: str
    severity: str = Field(default="Medium", description="High, Medium, Low")
    evidence_segment_id: int | None = None
    requires_review: bool = True
    resolved: bool = False


class SafetyAlertCreate(SafetyAlertBase):
    consultation_id: int


class SafetyAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    consultation_id: int
    type: str
    title: str
    detail: str
    severity: str
    evidence_segment_id: int | None = None
    requires_review: bool = True
    resolved: bool = False
    created_at: datetime | None = None
    evidence_segment: Optional[TranscriptSegmentResponse] = None

    # Frontend compatibility
    @computed_field
    @property
    def evidenceSegmentId(self) -> str | None:
        return str(self.evidence_segment_id) if self.evidence_segment_id is not None else None

    @computed_field
    @property
    def evidence_text(self) -> str | None:
        return self.evidence_segment.text if self.evidence_segment else None


class SafetyValidationResponse(BaseModel):
    consultation_id: int
    review_required: bool
    alert_count: int
    high_priority_alert_count: int
    alerts: list[SafetyAlertResponse]


class SafetySummaryResponse(SafetyValidationResponse):
    pass


class AlertResolveRequest(BaseModel):
    resolved: bool = True
