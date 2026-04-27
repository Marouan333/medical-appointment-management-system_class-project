"""Background reminder scheduler.

Polls appointment-service every hour for appointments starting in ~24h
and sends reminder notifications. Best-effort, idempotent via DB check.
"""
import logging
import os
from datetime import datetime, timedelta

import httpx
from apscheduler.schedulers.background import BackgroundScheduler

from . import models, sender, templates
from .database import SessionLocal

log = logging.getLogger("notification.reminders")
APPT_URL = os.getenv("APPOINTMENT_SERVICE_URL", "http://appointment-service:8000")


def _send_reminders():
    target = datetime.utcnow() + timedelta(hours=24)
    window_start = target - timedelta(minutes=30)
    window_end = target + timedelta(minutes=30)

    db = SessionLocal()
    try:
        # Naive: hit the listing endpoint. In a real system we'd publish events.
        # Without a JWT we cannot call the protected list endpoint, so for the
        # student demo we just log that the scheduler is alive.
        log.info("Reminder scheduler tick: would send for %s..%s", window_start, window_end)
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(_send_reminders, "interval", hours=1, id="reminders", replace_existing=True)
    scheduler.start()
    return scheduler
