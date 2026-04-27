"""Simple inline templates. In production, use Jinja2 / database-stored templates."""

TEMPLATES = {
    "appointment_created": {
        "subject": "Confirmation de votre rendez-vous",
        "body": "Bonjour,\n\nVotre rendez-vous a été créé pour le {start_at}.\nID: {appointment_id}\n\nMerci.",
    },
    "appointment_rescheduled": {
        "subject": "Rendez-vous reprogrammé",
        "body": "Votre rendez-vous {appointment_id} a été déplacé au {start_at}.",
    },
    "appointment_cancelled": {
        "subject": "Rendez-vous annulé",
        "body": "Votre rendez-vous {appointment_id} a été annulé.",
    },
    "appointment_reminder": {
        "subject": "Rappel: rendez-vous demain",
        "body": "Rappel: vous avez un rendez-vous à {start_at}.\nID: {appointment_id}",
    },
}


def render(template: str, payload: dict) -> tuple[str, str]:
    tpl = TEMPLATES.get(template, {"subject": template, "body": str(payload)})
    payload = payload or {}
    from string import Formatter
    keys = {fn for _, fn, _, _ in Formatter().parse(tpl["body"]) if fn}
    safe = {k: payload.get(k, f"{{{k}}}") for k in keys}
    keys_s = {fn for _, fn, _, _ in Formatter().parse(tpl["subject"]) if fn}
    safe_s = {k: payload.get(k, f"{{{k}}}") for k in keys_s}
    return tpl["subject"].format(**safe_s), tpl["body"].format(**safe)
