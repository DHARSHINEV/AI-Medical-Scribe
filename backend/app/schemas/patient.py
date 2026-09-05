from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, max_length=30)
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)


class PatientCreate(PatientBase):
    mrn: str = Field(min_length=1, max_length=50)


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, max_length=30)
    conditions: list[str] | None = None
    allergies: list[str] | None = None
    medications: list[str] | None = None


class PatientResponse(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mrn: str
    created_at: datetime
    updated_at: datetime