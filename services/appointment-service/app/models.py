import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    practitioner_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    start_at = Column(DateTime, nullable=False)
    end_at = Column(DateTime, nullable=False)
    status = Column(String(32), nullable=False, default="scheduled")
    # scheduled | confirmed | cancelled | completed | no_show
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    history = relationship("AppointmentHistory", back_populates="appointment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_appt_practitioner_start", "practitioner_id", "start_at"),
    )


class AppointmentHistory(Base):
    __tablename__ = "appointment_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id = Column(UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    note = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="history")
