from datetime import datetime
from pydantic import BaseModel, ConfigDict, computed_field
from app.schemas.transcript import TranscriptSegmentResponse


class ConsultationCreate(BaseModel):
    doctor_id: int | None = None


class ConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    patient_id: int
    doctor_id: int | None = None
    status: str
    stage: str
    audio_path: str | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    segments: list[TranscriptSegmentResponse] | None = None

    # Frontend camelCase alias
    @computed_field
    @property
    def patientId(self) -> str:
        return str(self.patient_id)


class AudioResponse(BaseModel):
    consultation_id: int
    filename: str
    path: str
    size_bytes: int
    jobId: str | None = None


class ConsultationApprovalResponse(BaseModel):
    id: int
    status: str
    stage: str
    approved: bool
    approved_at: datetime
    approved_by: int | None = None
    message: str = "Consultation successfully approved by clinician."