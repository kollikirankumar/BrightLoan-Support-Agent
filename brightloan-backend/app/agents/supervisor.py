import json
import re

from langchain_core.messages import SystemMessage, HumanMessage

from ..llm import get_llm
from ..logging_config import log_llm_call, logger
from ..state import SupportState

PROHIBITED_PATTERNS = [
    r"\bguarantee(d)?\b",
    r"\bdefinitely approved\b",
    r"\b100% approved\b",
]

SYSTEM_PROMPT = """You are reviewing a draft customer support response for
Brightloan, a lending company. Given the retrieved context and the draft
response, decide:

1. groundedness_ok: true if every factual claim in the draft (numbers,
   policy details, timelines) is supported by the context, false
   otherwise. This is the check that actually matters — the whole point
   is catching hallucinated financial/policy details.
2. verdict:
   - "approve": groundedness_ok is true, AND the tone isn't rude,
     hostile, or inappropriate. A warm, conversational, informal tone
     (e.g. "Hey Rajesh!", casual phrasing, addressing the user by first
     name) is completely normal for this product and should NEVER by
     itself cause anything other than "approve" — do not flag
     friendliness or informality as a problem.
   - "revise": groundedness_ok is false because of a specific, fixable
     issue (e.g. a claim not present in the context) that a rewrite
     could correct.
   - "escalate": the context genuinely doesn't contain the answer at
     all, so no rewrite of the draft could fix it.
3. notes: brief explanation.

Tone is a rare, minor secondary signal only — never a primary reason to
mark something other than "approve". If groundedness_ok is true, the
verdict should almost always be "approve" regardless of how casual the
phrasing is.

Respond with ONLY valid JSON:
{"groundedness_ok": true/false, "verdict": "approve"|"revise"|"escalate", "notes": "..."}
"""


def _rule_violations(draft: str) -> list:
    return [p for p in PROHIBITED_PATTERNS if re.search(p, draft, re.IGNORECASE)]


def supervise(state: SupportState) -> SupportState:
    rid = state.get("request_id", "?")
    revision_count = state.get("revision_count", 0)

    # Only RAG-generated answers need groundedness/tone review — handoff
    # and decline responses have no factual claims to check.
    if state.get("response_type") != "answer":
        logger.info(f"[{rid}] SUPERVISOR -> pass-through approve (response_type={state.get('response_type')!r}, no check needed)")
        return {
            **state,
            "supervisor_verdict": "approve",
            "supervisor_notes": "Non-answer response type; no groundedness check needed.",
            "final_text": state.get("final_text") or state.get("draft_response", ""),
        }

    draft = state.get("draft_response", "")
    violations = _rule_violations(draft)
    if violations:
        verdict = "escalate" if revision_count >= 1 else "revise"
        logger.info(f"[{rid}] SUPERVISOR -> {verdict} (rule violation(s): {violations}, revision_count was {revision_count})")
        return {
            **state,
            "supervisor_verdict": verdict,
            "supervisor_notes": f"Rule violation(s): {violations}",
            "revision_count": revision_count + 1,
        }

    retrieved_chunks = state.get("retrieved_chunks", [])
    context = "\n\n".join(c["content"] for c in retrieved_chunks)
    llm = get_llm(temperature=0, json_mode=True)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nDraft response:\n{draft}"),
    ]
    response = llm.invoke(messages)
    section_names = [c["metadata"].get("section") for c in retrieved_chunks]
    log_llm_call(
        rid, "supervisor", messages, response.content,
        human_summary=f"draft response (see RAG draft above) + context from sections: {section_names}",
    )

    try:
        parsed = json.loads(response.content)
        verdict = parsed.get("verdict", "approve")
        notes = parsed.get("notes", "")
    except (json.JSONDecodeError, TypeError):
        verdict, notes = "approve", "Supervisor response unparsable; defaulting to approve."

    logger.info(f"[{rid}] SUPERVISOR LLM verdict={verdict!r}, notes={notes!r} (revision_count so far: {revision_count})")

    # Loop protection: never allow a second "revise" — force escalate instead.
    if verdict == "revise" and revision_count >= 1:
        logger.info(f"[{rid}] SUPERVISOR -> loop protection triggered, forcing escalate instead of a second revise")
        verdict = "escalate"

    new_state = {**state, "supervisor_verdict": verdict, "supervisor_notes": notes}
    if verdict == "revise":
        new_state["revision_count"] = revision_count + 1
    elif verdict == "approve":
        new_state["final_text"] = draft
    return new_state
