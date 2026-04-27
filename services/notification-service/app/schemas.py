from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class NotificationSend(BaseModel):
    user_id: Optional[UUID] = None
    channel: Literal["email", "sms"] = "email"
    template: str
    recipient: Optional[str] = None  # email or phone; if missing, lookup by user_id
    payload: Optional[Dict[str, Any]] = None


class NotificationOut(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    channel: str
    template: str
    recipient: Optional[str]
    subject: Optional[str]
    body: Optional[str]
    status: str
    error: Optional[str]
    created_at: datetime
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True
