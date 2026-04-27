import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("notification.sender")


def send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body, charset="utf-8")
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        smtp.send_message(msg)


def send_sms(to: str, body: str) -> None:
    """Stub: prints to stdout. Replace with Twilio/etc. integration."""
    log.info("[SMS] to=%s body=%s", to, body)
