from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LabReportResponse(BaseModel):
    id: int
    patient_id: int
    consultation_id: Optional[int] = None
    title: str
    filename: str
    file_size_bytes: int
    mime_type: str
    uploaded_by: Optional[int] = None
    created_at: datetime
    file_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
