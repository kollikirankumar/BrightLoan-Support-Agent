import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")

# Handoff email notification — optional. If unset, the handoff agent still
# assigns a rep and responds normally; it just skips sending the email
# instead of failing the request. See app/notifications.py.
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
HANDOFF_FROM_EMAIL = os.getenv("HANDOFF_FROM_EMAIL", "onboarding@resend.dev")
HANDOFF_NOTIFICATION_EMAIL = os.getenv("HANDOFF_NOTIFICATION_EMAIL")

BACKEND_ROOT = Path(__file__).parent.parent

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
        "from console.groq.com."
    )
