from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    preferred_channel: Literal["email", "sms"] = "email"
    language: str = "fr"


class PatientUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    preferred_channel: Optional[Literal["email", "sms"]] = None
    language: Optional[str] = None


class HistoryCreate(BaseModel):
    condition: str
    notes: Optional[str] = None


class HistoryOut(BaseModel):
    id: UUID
    condition: str
    notes: Optional[str]
    recorded_at: datetime

    class Config:
        from_attributes = True


class PatientOut(BaseModel):
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    birth_date: Optional[date]
    phone: Optional[str]
    address: Optional[str]
    preferred_channel: str
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


class PatientWithHistory(PatientOut):
    history: List[HistoryOut] = []
