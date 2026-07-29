from langchain_groq import ChatGroq
from .config import GROQ_API_KEY, GROQ_MODEL


def get_llm(temperature: float = 0.2, json_mode: bool = False):
    kwargs = {}
    if json_mode:
        # Groq's API is OpenAI-compatible; this forces valid-JSON output
        # so classifier/supervisor parsing doesn't have to guess at format.
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    return ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=temperature, **kwargs)
