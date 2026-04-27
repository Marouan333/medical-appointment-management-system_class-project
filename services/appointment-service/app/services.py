"""Inter-service HTTP clients."""
import httpx

from .config import settings


def notify(payload: dict) -> None:
    """Fire-and-forget notification (best-effort)."""
    try:
        httpx.post(f"{settings.NOTIFICATION_SERVICE_URL}/notifications/send", json=payload, timeout=3.0)
    except Exception:
        pass


def patient_exists(patient_id: str, token: str) -> bool:
    try:
        resp = httpx.get(
            f"{settings.PATIENT_SERVICE_URL}/patients/{patient_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=3.0,
        )
        return resp.status_code == 200
    except Exception:
        return False


def practitioner_exists(practitioner_id: str) -> bool:
    try:
        resp = httpx.get(
            f"{settings.PRACTITIONER_SERVICE_URL}/practitioners/{practitioner_id}",
            timeout=3.0,
        )
        return resp.status_code == 200
    except Exception:
        return False
