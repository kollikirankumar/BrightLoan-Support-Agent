import logging
import sys

from .config import BACKEND_ROOT

LOG_DIR = BACKEND_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "requests.log"


def _setup():
    logger = logging.getLogger("brightloan")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger  # avoid duplicate handlers if this module reloads

    formatter = logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# One shared logger every agent imports — writes to both the terminal
# running uvicorn AND logs/requests.log, so you can `tail -f` the file
# separately from wherever the server happens to be running.
logger = _setup()


def log_request_separator() -> None:
    """Writes a genuine blank line (no timestamp) directly to each
    handler's stream, bypassing the formatter — call before logging a new
    request so consecutive requests are visually easy to tell apart."""
    for handler in logger.handlers:
        stream = getattr(handler, "stream", None)
        if stream:
            stream.write("\n")
            stream.flush()


def log_llm_call(
    rid: str, label: str, messages, response_content: str, human_summary: str = None
) -> None:
    """Logs what's sent to Groq and the raw response received, for every
    LLM call. The system prompt is static per agent, so it's referenced by
    file instead of printed in full. The human/user content is logged in
    full by default — pass human_summary to replace it with a short
    reference instead, for calls whose content (e.g. full retrieved KB
    chunks) was already printed in full by an earlier log line, so it
    isn't repeated twice."""
    logger.info(f"[{rid}] LLM CALL ({label}) >>> SENDING:")
    for m in messages:
        role = m.__class__.__name__.replace("Message", "")  # System | Human
        if role == "System":
            logger.info(f"[{rid}]   [System] <{label} prompt — see app/agents/{label}.py>")
        else:
            content = human_summary if human_summary is not None else m.content
            logger.info(f"[{rid}]   [{role}] {content}")
    logger.info(f"[{rid}] LLM CALL ({label}) <<< RAW RESPONSE: {response_content!r}")
