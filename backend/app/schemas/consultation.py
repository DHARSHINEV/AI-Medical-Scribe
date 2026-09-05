from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsultationCreate(BaseModel):
    doctor_id: int | None = None


class ConsultationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    doctor_id: int | None
    status: str
    stage: str
    audio_path: str | None
    created_at: datetime
    updated_at: datetime

class AudioResponse(BaseModel):
    consultation_id: int
    filename: str
    path: str
    size_bytes: int