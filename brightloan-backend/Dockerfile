FROM python:3.11-slim

WORKDIR /app

# sentence-transformers/torch are deliberately NOT installed here — see
# requirements-reranker.txt. The reranker is disabled (USE_RERANKER=False
# in app/agents/rag_query.py) because Render's free tier (512MB) can't fit
# torch alongside the rest of the stack. Keeping it out of the image also
# avoids langchain_core's optional GPT2TokenizerFast import silently
# pulling torch back in at startup.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# app/config.py requires GROQ_API_KEY to import at all (fails fast if
# misconfigured at runtime). This placeholder only satisfies that check
# while ingesting the KB at build time — Render's real env var overrides
# it when the container actually starts.
ENV GROQ_API_KEY=docker-build-placeholder
RUN python -m app.vectorstore.ingest

# 7860 is Hugging Face Spaces' expected default port for Docker Spaces.
# Render sets $PORT itself (e.g. 10000), which always overrides this
# fallback, so this change is safe for both platforms.
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
