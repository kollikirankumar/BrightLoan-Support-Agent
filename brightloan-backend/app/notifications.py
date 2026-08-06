from typing import Optional

import resend

from .config import RESEND_API_KEY, HANDOFF_FROM_EMAIL, HANDOFF_NOTIFICATION_EMAIL
from .logging_config import logger

resend.api_key = RESEND_API_KEY


def send_handoff_notification(
    user_name: str,
    phone_number: Optional[str],
    query: str,
    rep_name: str,
    specialty: str,
    reason: str,
) -> None:
    """Best-effort sales-lead email, run as a FastAPI background task (see
    main.py) so it never adds latency to the chat response. Never raises —
    a failed/unconfigured send must not affect anything the customer sees,
    since the handoff itself already succeeded by this point.
    """
    if not RESEND_API_KEY or not HANDOFF_NOTIFICATION_EMAIL:
        logger.info("Email notification skipped — RESEND_API_KEY or HANDOFF_NOTIFICATION_EMAIL not set.")
        return

    phone_display = phone_number or "not provided"

    try:
        result = resend.Emails.send({
            "from": HANDOFF_FROM_EMAIL,
            "to": [HANDOFF_NOTIFICATION_EMAIL],
            "subject": f"New sales lead: {user_name} ({phone_display})",
            "html": (
                f"<p><strong>Customer:</strong> {user_name}</p>"
                f"<p><strong>Phone number:</strong> {phone_display}</p>"
                f"<p><strong>Query:</strong> {query}</p>"
                f"<p><strong>Reason for handoff:</strong> {reason}</p>"
                f"<p><strong>Routed internally to:</strong> {rep_name} ({specialty})</p>"
            ),
        })
        logger.info(f"Handoff notification email sent to {HANDOFF_NOTIFICATION_EMAIL} — id={result.get('id')}")
    except Exception as e:
        logger.exception(f"Failed to send handoff notification email: {e}")
