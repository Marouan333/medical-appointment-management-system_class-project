import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Practitioner(Base):
    __tablename__ = "practitioners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialty = Column(String(100), nullable=False, index=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    schedules = relationship("Schedule", back_populates="practitioner", cascade="all, delete-orphan")
    overrides = relationship("AvailabilityOverride", back_populates="practitioner", cascade="all, delete-orphan")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practitioner_id = Column(UUID(as_uuid=True), ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday ... 6 = Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_min = Column(Integer, default=30, nullable=False)

    practitioner = relationship("Practitioner", back_populates="schedules")


class AvailabilityOverride(Base):
    __tablename__ = "availability_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    practitioner_id = Column(UUID(as_uuid=True), ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    is_available = Column(Boolean, default=False, nullable=False)
    reason = Column(String(255), nullable=True)

    practitioner = relationship("Practitioner", back_populates="overrides")
