from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    user_id: Optional[int] = None
    consultation_id: Optional[int] = None
    details: Optional[dict[str, Any]] = None
    created_at: datetime
