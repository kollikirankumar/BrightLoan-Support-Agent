import json

from ..config import BACKEND_ROOT
from ..logging_config import logger
from ..state import SupportState

ROSTER_PATH = BACKEND_ROOT / "app" / "data" / "roster.json"

# Routing categories that aren't real job specialties — used internally
# for rep matching only, never shown to the customer.
NON_SPECIALTY_INTENTS = {"human_handoff_request", "account_specific"}


def _load_roster():
    return json.loads(ROSTER_PATH.read_text())


def assign_rep(state: SupportState) -> SupportState:
    roster = _load_roster()
    intent = state.get("intent", "general_faq")
    name = state.get("user_name") or "there"

    matches = [r for r in roster if intent in r.get("specialty", []) and r["status"] == "active"]
    if not matches:
        matches = [r for r in roster if r["status"] == "active"]
    if not matches:
        logger.info(f"[{state.get('request_id', '?')}] HANDOFF -> no active reps available")
        return {
            **state,
            "response_type": "handoff",
            "final_text": "All our sales officers are currently offline. Please try again shortly.",
        }

    rep = matches[0]
    real_specialties = [s for s in rep["specialty"] if s not in NON_SPECIALTY_INTENTS]
    specialty_label = (real_specialties[0] if real_specialties else "general_support").replace("_", " ")

    # Customer never sees a rep name or a slot anymore — this is a lead
    # handoff (phone number shared internally), not a booked appointment.
    # The rep/specialty is still tracked internally for the notification
    # email main.py sends as a background task.
    if intent == "account_specific":
        reason = "Asked about their own account/loan — not connected to real data yet."
        message = (
            f"I can't pull up your account details yet — that feature isn't "
            f"connected. I've shared your phone number and question with our "
            f"sales team, and one of our officers will contact you shortly "
            f"to help directly."
        )
    elif intent == "human_handoff_request":
        reason = "Explicitly asked to speak with a person."
        message = (
            f"Thanks, {name} — I've shared your phone number and query with "
            f"our sales team, and one of our officers will contact you shortly."
        )
    else:
        # A static-info intent (loan_process/offer_amount/company_policy/
        # general_faq) landed here because RAG found nothing in the KB —
        # see route_after_rag in graph.py.
        reason = "Question wasn't covered by the knowledge base."
        message = (
            f"I don't have that specific information on file — I've shared "
            f"your phone number and question with our sales team, and one of "
            f"our officers will contact you shortly to help directly."
        )

    rid = state.get("request_id", "?")
    logger.info(
        f"[{rid}] HANDOFF -> assigned {rep['name']} ({specialty_label}), reason={reason!r}"
    )

    return {
        **state,
        "response_type": "handoff",
        "assigned_agent": {"id": rep["id"], "name": rep["name"], "specialty": specialty_label},
        "handoff_reason": reason,
        "final_text": message,
    }
