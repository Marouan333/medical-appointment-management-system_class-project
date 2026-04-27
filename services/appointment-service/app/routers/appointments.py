from datetime import date, datetime, time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .. import models, schemas, security, services
from ..database import get_db

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _conflict_exists(db: Session, practitioner_id: UUID, start_at: datetime, end_at: datetime,
                     exclude_id: Optional[UUID] = None) -> bool:
    q = db.query(models.Appointment).filter(
        models.Appointment.practitioner_id == practitioner_id,
        models.Appointment.status.in_(["scheduled", "confirmed"]),
        and_(models.Appointment.start_at < end_at, models.Appointment.end_at > start_at),
    )
    if exclude_id:
        q = q.filter(models.Appointment.id != exclude_id)
    return db.query(q.exists()).scalar()


def _log(db: Session, appt_id: UUID, action: str, actor_id: Optional[str], note: str = None):
    db.add(models.AppointmentHistory(
        appointment_id=appt_id, action=action,
        actor_id=actor_id if actor_id else None,
        note=note,
    ))


@router.post("", response_model=schemas.AppointmentOut, status_code=201)
def create_appointment(data: schemas.AppointmentCreate, db: Session = Depends(get_db),
                       current=Depends(security.get_current_user)):
    if data.end_at <= data.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    if data.start_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot book in the past")

    if not services.practitioner_exists(str(data.practitioner_id)):
        raise HTTPException(status_code=404, detail="Practitioner not found")

    if _conflict_exists(db, data.practitioner_id, data.start_at, data.end_at):
        raise HTTPException(status_code=409, detail="Time slot conflicts with another appointment")

    appt = models.Appointment(**data.model_dump(), status="scheduled")
    db.add(appt)
    db.flush()
    _log(db, appt.id, "created", current["user_id"])
    db.commit()
    db.refresh(appt)

    services.notify({
        "user_id": current["user_id"],
        "channel": "email",
        "template": "appointment_created",
        "payload": {
            "appointment_id": str(appt.id),
            "start_at": appt.start_at.isoformat(),
            "practitioner_id": str(appt.practitioner_id),
        },
    })
    return appt


@router.get("", response_model=List[schemas.AppointmentOut])
def list_appointments(
    patient_id: Optional[UUID] = None,
    practitioner_id: Optional[UUID] = None,
    status: Optional[str] = None,
    appt_date: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current=Depends(security.get_current_user),
):
    q = db.query(models.Appointment)
    if patient_id:
        q = q.filter(models.Appointment.patient_id == patient_id)
    if practitioner_id:
        q = q.filter(models.Appointment.practitioner_id == practitioner_id)
    if status:
        q = q.filter(models.Appointment.status == status)
    if appt_date:
        day_start = datetime.combine(appt_date, time.min)
        day_end = datetime.combine(appt_date, time.max)
        q = q.filter(and_(models.Appointment.start_at >= day_start,
                          models.Appointment.start_at <= day_end))
    return q.order_by(models.Appointment.start_at).all()


@router.get("/{appointment_id}", response_model=schemas.AppointmentWithHistory)
def get_appointment(appointment_id: UUID, db: Session = Depends(get_db),
                    current=Depends(security.get_current_user)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appt


@router.put("/{appointment_id}", response_model=schemas.AppointmentOut)
def update_appointment(appointment_id: UUID, data: schemas.AppointmentUpdate,
                       db: Session = Depends(get_db), current=Depends(security.get_current_user)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status in ("cancelled", "completed"):
        raise HTTPException(status_code=400, detail=f"Cannot modify a {appt.status} appointment")

    new_start = data.start_at or appt.start_at
    new_end = data.end_at or appt.end_at
    if new_end <= new_start:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    if _conflict_exists(db, appt.practitioner_id, new_start, new_end, exclude_id=appt.id):
        raise HTTPException(status_code=409, detail="Time slot conflicts")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)
    _log(db, appt.id, "rescheduled", current["user_id"])
    db.commit()
    db.refresh(appt)

    services.notify({
        "user_id": current["user_id"],
        "channel": "email",
        "template": "appointment_rescheduled",
        "payload": {"appointment_id": str(appt.id), "start_at": appt.start_at.isoformat()},
    })
    return appt


@router.delete("/{appointment_id}", response_model=schemas.AppointmentOut)
def cancel_appointment(appointment_id: UUID, db: Session = Depends(get_db),
                       current=Depends(security.get_current_user)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Already cancelled")
    appt.status = "cancelled"
    _log(db, appt.id, "cancelled", current["user_id"])
    db.commit()
    db.refresh(appt)

    services.notify({
        "user_id": current["user_id"],
        "channel": "email",
        "template": "appointment_cancelled",
        "payload": {"appointment_id": str(appt.id)},
    })
    return appt


@router.post("/{appointment_id}/confirm", response_model=schemas.AppointmentOut)
def confirm_appointment(appointment_id: UUID, db: Session = Depends(get_db),
                        current=Depends(security.require_roles("secretary", "practitioner", "admin"))):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status != "scheduled":
        raise HTTPException(status_code=400, detail=f"Cannot confirm from status {appt.status}")
    appt.status = "confirmed"
    _log(db, appt.id, "confirmed", current["user_id"])
    db.commit()
    db.refresh(appt)
    return appt


@router.post("/{appointment_id}/no-show", response_model=schemas.AppointmentOut)
def mark_no_show(appointment_id: UUID, db: Session = Depends(get_db),
                 current=Depends(security.require_roles("secretary", "practitioner", "admin"))):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "no_show"
    _log(db, appt.id, "no_show", current["user_id"])
    db.commit()
    db.refresh(appt)
    return appt


@router.post("/{appointment_id}/complete", response_model=schemas.AppointmentOut)
def complete_appointment(appointment_id: UUID, db: Session = Depends(get_db),
                         current=Depends(security.require_roles("practitioner", "admin"))):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    appt.status = "completed"
    _log(db, appt.id, "completed", current["user_id"])
    db.commit()
    db.refresh(appt)
    return appt


# ===== Internal endpoints (called by other services) =====

@router.get("/internal/booked", response_model=List[schemas.BookedSlot])
def booked_slots(practitioner_id: UUID, date_from: date, date_to: date, db: Session = Depends(get_db)):
    """Lightweight internal endpoint: returns active booked slots for availability calc."""
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to, time.max)
    rows = db.query(models.Appointment).filter(
        models.Appointment.practitioner_id == practitioner_id,
        models.Appointment.status.in_(["scheduled", "confirmed"]),
        models.Appointment.start_at >= start,
        models.Appointment.start_at <= end,
    ).all()
    return [schemas.BookedSlot(start_at=r.start_at, end_at=r.end_at) for r in rows]
