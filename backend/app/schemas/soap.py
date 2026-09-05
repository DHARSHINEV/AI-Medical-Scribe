from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field


class SOAPNoteBase(BaseModel):
    subjective: str = Field(default="")
    objective: str = Field(default="")
    assessment: str = Field(default="")
    plan: str = Field(default="")


class SOAPNoteCreate(SOAPNoteBase):
    consultation_id: int


class SOAPNoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


class SOAPNoteResponse(SOAPNoteBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    consultation_id: int
    approved: bool = False
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Frontend camelCase aliases
    @computed_field
    @property
    def consultationId(self) -> str:
        return str(self.consultation_id)

    @computed_field
    @property
    def updatedAt(self) -> str | None:
        return self.updated_at.isoformat() if self.updated_at else None
