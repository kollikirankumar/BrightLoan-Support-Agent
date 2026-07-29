from typing import TypedDict, List, Dict, Optional


class SupportState(TypedDict, total=False):
    # Correlates every log line across agents to one /chat call — see
    # logging_config.py and app/main.py.
    request_id: str

    # Identity — passed in from the request; real session/auth verification
    # lands later per 02-frontend-react-auth.md.
    user_name: str
    user_email: Optional[str]
    phone_number: Optional[str]

    # Conversation
    user_query: str
    chat_history: List[Dict]

    # Classifier output — standalone_query is user_query rewritten to be
    # self-contained using chat_history (resolves "it"/"that"/follow-ups);
    # RAG uses this for both retrieval and generation, not the raw query.
    intent: str
    intent_confidence: float
    standalone_query: str

    # RAG agent output
    retrieved_chunks: List[Dict]
    draft_response: str
    citations: List[str]

    # Handoff agent output — internal only, never sent to the customer;
    # main.py uses these to build the background email notification.
    assigned_agent: Optional[Dict]
    scheduled_slot: Optional[str]
    handoff_reason: Optional[str]

    # Supervisor output
    supervisor_verdict: str
    supervisor_notes: str
    revision_count: int

    # Final
    response_type: str  # "answer" | "handoff" | "decline"
    final_text: str
