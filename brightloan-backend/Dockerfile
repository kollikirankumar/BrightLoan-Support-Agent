FROM python:3.11-slim

WORKDIR /app

# CPU-only torch first — avoids pulling multi-GB CUDA deps that
# sentence-transformers would otherwise drag in by default.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# app/config.py requires GROQ_API_KEY to import at all (fails fast if
# misconfigured at runtime). This placeholder only satisfies that check
# while ingesting the KB at build time — Render's real env var overrides
# it when the container actually starts.
ENV GROQ_API_KEY=docker-build-placeholder
RUN python -m app.vectorstore.ingest

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
