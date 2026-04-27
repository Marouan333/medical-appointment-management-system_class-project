from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PractitionerCreate(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    specialty: str
    bio: Optional[str] = None


class PractitionerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    specialty: Optional[str] = None
    bio: Optional[str] = None


class PractitionerOut(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    specialty: str
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduleItem(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    slot_duration_min: int = 30


class ScheduleOut(ScheduleItem):
    id: UUID

    class Config:
        from_attributes = True


class ScheduleSet(BaseModel):
    schedules: List[ScheduleItem]


class OverrideCreate(BaseModel):
    date: date
    is_available: bool = False
    reason: Optional[str] = None


class OverrideOut(OverrideCreate):
    id: UUID

    class Config:
        from_attributes = True


class Slot(BaseModel):
    start: datetime
    end: datetime


class AvailabilityResponse(BaseModel):
    practitioner_id: UUID
    slots: List[Slot]
