import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    channel = Column(String(16), nullable=False)  # email | sms
    template = Column(String(64), nullable=False)
    recipient = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    status = Column(String(32), nullable=False, default="pending")  # pending | sent | failed
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_at = Column(DateTime, nullable=True)
