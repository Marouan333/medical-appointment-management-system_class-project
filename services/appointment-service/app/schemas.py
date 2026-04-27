from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

Status = Literal["scheduled", "confirmed", "cancelled", "completed", "no_show"]


class AppointmentCreate(BaseModel):
    patient_id: UUID
    practitioner_id: UUID
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None


class AppointmentUpdate(BaseModel):
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    reason: Optional[str] = None


class AppointmentOut(BaseModel):
    id: UUID
    patient_id: UUID
    practitioner_id: UUID
    start_at: datetime
    end_at: datetime
    status: Status
    reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HistoryEntry(BaseModel):
    id: UUID
    action: str
    actor_id: Optional[UUID]
    timestamp: datetime
    note: Optional[str]

    class Config:
        from_attributes = True


class AppointmentWithHistory(AppointmentOut):
    history: List[HistoryEntry] = []


class BookedSlot(BaseModel):
    start_at: datetime
    end_at: datetime
