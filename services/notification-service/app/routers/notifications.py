from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, sender, templates
from ..database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send", response_model=schemas.NotificationOut, status_code=201)
def send_notification(data: schemas.NotificationSend, db: Session = Depends(get_db)):
    subject, body = templates.render(data.template, data.payload or {})

    notif = models.Notification(
        user_id=data.user_id,
        channel=data.channel,
        template=data.template,
        recipient=data.recipient,
        subject=subject,
        body=body,
        payload=data.payload,
        status="pending",
    )
    db.add(notif)
    db.flush()

    try:
        recipient = data.recipient or "demo@medical-rdv.local"  # fallback for student demo
        if data.channel == "email":
            sender.send_email(recipient, subject, body)
        else:
            sender.send_sms(recipient, body)
        notif.status = "sent"
        notif.sent_at = datetime.utcnow()
    except Exception as exc:
        notif.status = "failed"
        notif.error = str(exc)

    db.commit()
    db.refresh(notif)
    return notif


@router.get("", response_model=List[schemas.NotificationOut])
def list_notifications(user_id: Optional[UUID] = None, status: Optional[str] = None,
                       db: Session = Depends(get_db)):
    q = db.query(models.Notification)
    if user_id:
        q = q.filter(models.Notification.user_id == user_id)
    if status:
        q = q.filter(models.Notification.status == status)
    return q.order_by(models.Notification.created_at.desc()).limit(200).all()


@router.get("/{notification_id}", response_model=schemas.NotificationOut)
def get_notification(notification_id: UUID, db: Session = Depends(get_db)):
    n = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n
