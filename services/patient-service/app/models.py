import uuid
from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=True)
    phone = Column(String(32), nullable=True)
    address = Column(String(255), nullable=True)
    preferred_channel = Column(String(16), default="email", nullable=False)  # email | sms
    language = Column(String(8), default="fr", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    history = relationship("MedicalHistory", back_populates="patient", cascade="all, delete-orphan")


class MedicalHistory(Base):
    __tablename__ = "medical_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    condition = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    patient = relationship("Patient", back_populates="history")
