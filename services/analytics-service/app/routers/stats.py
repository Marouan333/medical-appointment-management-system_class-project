from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/practitioner/{practitioner_id}")
def practitioner_stats(
    practitioner_id: UUID,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    _=Depends(security.require_roles("practitioner", "secretary", "admin")),
):
    df = date_from or (date.today() - timedelta(days=30))
    dt = date_to or date.today()
    start = datetime.combine(df, time.min)
    end = datetime.combine(dt, time.max)

    sql = text("""
        SELECT status, COUNT(*) AS n
          FROM appointments
         WHERE practitioner_id = :pid
           AND start_at BETWEEN :s AND :e
         GROUP BY status
    """)
    rows = db.execute(sql, {"pid": str(practitioner_id), "s": start, "e": end}).fetchall()
    counts = {r[0]: r[1] for r in rows}
    total = sum(counts.values()) or 0
    no_shows = counts.get("no_show", 0)
    cancellations = counts.get("cancelled", 0)
    completed = counts.get("completed", 0)
    fill_rate = round((completed + counts.get("confirmed", 0)) / total, 3) if total else 0.0

    return {
        "practitioner_id": str(practitioner_id),
        "date_from": df.isoformat(),
        "date_to": dt.isoformat(),
        "total_appointments": total,
        "by_status": counts,
        "no_show_rate": round(no_shows / total, 3) if total else 0.0,
        "cancellation_rate": round(cancellations / total, 3) if total else 0.0,
        "fill_rate": fill_rate,
    }


@router.get("/daily")
def daily_activity(appt_date: date = Query(..., alias="date"), db: Session = Depends(get_db),
                   _=Depends(security.require_roles("practitioner", "secretary", "admin"))):
    start = datetime.combine(appt_date, time.min)
    end = datetime.combine(appt_date, time.max)
    sql = text("""
        SELECT EXTRACT(HOUR FROM start_at)::int AS hour, COUNT(*) AS n
          FROM appointments
         WHERE start_at BETWEEN :s AND :e
         GROUP BY hour
         ORDER BY hour
    """)
    rows = db.execute(sql, {"s": start, "e": end}).fetchall()
    hourly = [{"hour": r[0], "count": r[1]} for r in rows]
    total = sum(r[1] for r in rows)
    return {"date": appt_date.isoformat(), "total_appointments": total, "hourly": hourly}


@router.get("/no-shows")
def no_show_ranking(
    limit: int = 10,
    date_from: Optional[date] = None,
    db: Session = Depends(get_db),
    _=Depends(security.require_roles("secretary", "admin")),
):
    df = date_from or (date.today() - timedelta(days=90))
    sql = text("""
        SELECT patient_id, COUNT(*) AS n
          FROM appointments
         WHERE status = 'no_show'
           AND start_at >= :s
         GROUP BY patient_id
         ORDER BY n DESC
         LIMIT :lim
    """)
    rows = db.execute(sql, {"s": datetime.combine(df, time.min), "lim": limit}).fetchall()
    return [{"patient_id": str(r[0]), "no_shows": r[1]} for r in rows]


@router.get("/peak-hours")
def peak_hours(
    days: int = 30,
    db: Session = Depends(get_db),
    _=Depends(security.require_roles("practitioner", "secretary", "admin")),
):
    start = datetime.utcnow() - timedelta(days=days)
    sql = text("""
        SELECT EXTRACT(HOUR FROM start_at)::int AS hour, COUNT(*) AS n
          FROM appointments
         WHERE start_at >= :s
         GROUP BY hour
         ORDER BY n DESC
    """)
    rows = db.execute(sql, {"s": start}).fetchall()
    return {"window_days": days, "hourly_distribution": [{"hour": r[0], "count": r[1]} for r in rows]}


@router.get("/overview")
def global_overview(db: Session = Depends(get_db),
                    _=Depends(security.require_roles("admin"))):
    sql = text("""
        SELECT status, COUNT(*) FROM appointments GROUP BY status
    """)
    rows = db.execute(sql).fetchall()
    counts = {r[0]: r[1] for r in rows}
    total = sum(counts.values())
    return {"total_appointments": total, "by_status": counts}
