from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field


class TranscriptSegmentBase(BaseModel):
    speaker: str = Field(default="Unassigned")
    text: str = Field(min_length=1)
    start_time: float = Field(default=0.0)
    end_time: float = Field(default=0.0)
    confidence: float | None = None


class TranscriptSegmentCreate(TranscriptSegmentBase):
    consultation_id: int


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    consultation_id: int
    speaker: str
    text: str
    start_time: float
    end_time: float
    confidence: float | None = None
    created_at: datetime | None = None

    # Frontend compatibility fields
    @computed_field
    @property
    def startTime(self) -> float:
        return self.start_time

    @computed_field
    @property
    def endTime(self) -> float:
        return self.end_time

    @computed_field
    @property
    def time(self) -> str:
        start_min = int(self.start_time // 60)
        start_sec = int(self.start_time % 60)
        end_min = int(self.end_time // 60)
        end_sec = int(self.end_time % 60)
        return f"{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}"


class FullTranscriptResponse(BaseModel):
    consultation_id: int
    text: str
    language: str = "en"
    segments: list[TranscriptSegmentResponse]
