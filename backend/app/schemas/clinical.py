from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field


class ClinicalEntityBase(BaseModel):
    type: str = Field(description="symptom, condition, medication, allergy, finding, etc.")
    value: str
    label: str | None = None
    status: str = Field(default="present", description="present, absent, uncertain, historical")
    confidence: float | None = None
    evidence_segment_id: int | None = None


class ClinicalEntityCreate(ClinicalEntityBase):
    consultation_id: int


class ClinicalEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    consultation_id: int
    type: str
    value: str
    label: str | None = None
    status: str
    confidence: float | None = None
    evidence_segment_id: int | None = None
    created_at: datetime | None = None

    # Frontend camelCase alias
    @computed_field
    @property
    def evidenceSegmentId(self) -> str | None:
        return str(self.evidence_segment_id) if self.evidence_segment_id is not None else None


class ClinicalExtractResponse(BaseModel):
    consultation_id: int
    entities: list[ClinicalEntityResponse]
