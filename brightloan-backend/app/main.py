import uuid
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

HISTORY_TURNS = 5  # last 5 turns (~10 messages) — bounds token cost, oldest just fall off

from .graph import SUPPORT_GRAPH
from .logging_config import log_request_separator, logger
from .notifications import send_handoff_notification

app = FastAPI(title="Brightloan Support Backend")

# Dev-mode CORS: the frontend currently identifies the user client-side
# (see brightloan-support-ui's loginAsGuest) and sends user_name with every
# request instead of relying on a session cookie. Tighten this once real
# Google-auth session verification lands per 02-frontend-react-auth.md.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    user_name: str = "there"
    phone_number: Optional[str] = None
    chat_history: List[ChatMessage] = []


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    request_id = uuid.uuid4().hex[:8]
    log_request_separator()
    logger.info(f"[{request_id}] ===== NEW REQUEST ({req.user_name}) =====")
    logger.info(f"[{request_id}] USER QUERY: {req.message!r}  (history: {len(req.chat_history)} msgs)")

    history = [m.model_dump() for m in req.chat_history[-HISTORY_TURNS * 2 :]]
    initial_state = {
        "request_id": request_id,
        "user_name": req.user_name,
        "phone_number": req.phone_number,
        "user_query": req.message,
        "chat_history": history,
        "revision_count": 0,
    }
    result = SUPPORT_GRAPH.invoke(initial_state)

    if result.get("response_type") == "handoff":
        assigned = result.get("assigned_agent")
        if assigned:
            # Fire-and-forget — runs after the response is sent, so the
            # customer never waits on email latency (see notifications.py).
            background_tasks.add_task(
                send_handoff_notification,
                user_name=req.user_name,
                phone_number=req.phone_number,
                query=req.message,
                rep_name=assigned.get("name", "unassigned"),
                specialty=assigned.get("specialty", "general support"),
                reason=result.get("handoff_reason", "unspecified"),
            )
        response = {"type": "handoff", "message": result.get("final_text", "")}
        logger.info(f"[{request_id}] FINAL RESPONSE (handoff): {response['message']!r}")
        return response

    response = {
        "type": "answer",
        "text": result.get("final_text") or result.get("draft_response", ""),
        "citations": result.get("citations", []),
    }
    logger.info(f"[{request_id}] FINAL RESPONSE (answer): {response['text']!r}")
    return response
