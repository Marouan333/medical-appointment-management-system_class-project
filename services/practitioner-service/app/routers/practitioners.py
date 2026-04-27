from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
import os

router = APIRouter(prefix="/practitioners", tags=["practitioners"])


@router.post("", response_model=schemas.PractitionerOut, status_code=201)
def create_practitioner(data: schemas.PractitionerCreate, db: Session = Depends(get_db),
                        current=Depends(security.require_roles("practitioner", "admin"))):
    if db.query(models.Practitioner).filter(models.Practitioner.user_id == current["user_id"]).first():
        raise HTTPException(status_code=409, detail="Practitioner profile already exists")
    p = models.Practitioner(user_id=current["user_id"], **data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("", response_model=List[schemas.PractitionerOut])
def list_practitioners(specialty: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(models.Practitioner)
    if specialty:
        q = q.filter(models.Practitioner.specialty.ilike(f"%{specialty}%"))
    return q.all()


@router.get("/{practitioner_id}", response_model=schemas.PractitionerOut)
def get_practitioner(practitioner_id: UUID, db: Session = Depends(get_db)):
    p = db.query(models.Practitioner).filter(models.Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    return p


@router.put("/{practitioner_id}", response_model=schemas.PractitionerOut)
def update_practitioner(practitioner_id: UUID, data: schemas.PractitionerUpdate,
                        db: Session = Depends(get_db),
                        current=Depends(security.require_roles("practitioner", "admin"))):
    p = db.query(models.Practitioner).filter(models.Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    if current["role"] != "admin" and str(p.user_id) != current["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{practitioner_id}/schedule", response_model=List[schemas.ScheduleOut])
def set_schedule(practitioner_id: UUID, data: schemas.ScheduleSet, db: Session = Depends(get_db),
                 current=Depends(security.require_roles("practitioner", "admin"))):
    p = db.query(models.Practitioner).filter(models.Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    if current["role"] != "admin" and str(p.user_id) != current["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    db.query(models.Schedule).filter(models.Schedule.practitioner_id == practitioner_id).delete()
    new_items = [models.Schedule(practitioner_id=practitioner_id, **s.model_dump()) for s in data.schedules]
    db.add_all(new_items)
    db.commit()
    for s in new_items:
        db.refresh(s)
    return new_items


@router.get("/{practitioner_id}/schedule", response_model=List[schemas.ScheduleOut])
def get_schedule(practitioner_id: UUID, db: Session = Depends(get_db)):
    return db.query(models.Schedule).filter(models.Schedule.practitioner_id == practitioner_id).all()


@router.post("/{practitioner_id}/overrides", response_model=schemas.OverrideOut, status_code=201)
def add_override(practitioner_id: UUID, data: schemas.OverrideCreate, db: Session = Depends(get_db),
                 current=Depends(security.require_roles("practitioner", "secretary", "admin"))):
    p = db.query(models.Practitioner).filter(models.Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    o = models.AvailabilityOverride(practitioner_id=practitioner_id, **data.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.get("/{practitioner_id}/availability", response_model=schemas.AvailabilityResponse)
def get_availability(
    practitioner_id: UUID,
    date_from: date = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: date = Query(..., description="End date inclusive (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    p = db.query(models.Practitioner).filter(models.Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Practitioner not found")
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")

    schedules = db.query(models.Schedule).filter(models.Schedule.practitioner_id == practitioner_id).all()
    overrides = {o.date: o for o in db.query(models.AvailabilityOverride).filter(
        models.AvailabilityOverride.practitioner_id == practitioner_id,
        models.AvailabilityOverride.date >= date_from,
        models.AvailabilityOverride.date <= date_to,
    ).all()}

    booked_slots = _fetch_booked_slots(practitioner_id, date_from, date_to)

    slots: list[schemas.Slot] = []
    cur = date_from
    while cur <= date_to:
        ovr = overrides.get(cur)
        if ovr is not None and not ovr.is_available:
            cur += timedelta(days=1)
            continue
        dow = cur.weekday()
        for sch in [s for s in schedules if s.day_of_week == dow]:
            slot_start = datetime.combine(cur, sch.start_time)
            day_end = datetime.combine(cur, sch.end_time)
            while slot_start + timedelta(minutes=sch.slot_duration_min) <= day_end:
                slot_end = slot_start + timedelta(minutes=sch.slot_duration_min)
                if not _is_booked(slot_start, slot_end, booked_slots):
                    slots.append(schemas.Slot(start=slot_start, end=slot_end))
                slot_start = slot_end
        cur += timedelta(days=1)

    return schemas.AvailabilityResponse(practitioner_id=practitioner_id, slots=slots)


def _fetch_booked_slots(practitioner_id: UUID, date_from: date, date_to: date) -> list[tuple[datetime, datetime]]:
    """Best-effort fetch of booked slots from appointment-service. Returns [] on failure."""
    url = os.getenv("APPOINTMENT_SERVICE_URL", "http://appointment-service:8000")
    try:
        resp = httpx.get(
            f"{url}/appointments/internal/booked",
            params={
                "practitioner_id": str(practitioner_id),
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            },
            timeout=3.0,
        )
        if resp.status_code != 200:
            return []
        return [(datetime.fromisoformat(r["start_at"]), datetime.fromisoformat(r["end_at"])) for r in resp.json()]
    except Exception:
        return []


def _is_booked(start: datetime, end: datetime, booked: list[tuple[datetime, datetime]]) -> bool:
    for b_start, b_end in booked:
        if start < b_end and end > b_start:
            return True
    return False
