# brightloan-backend

FastAPI + LangGraph backend implementing the multi-agent graph from
[`../01-architecture.md`](../01-architecture.md): Classifier → RAG Query
Agent / Human Handoff Agent → Supervisor.

## Setup

Requires **Python 3.10+** (LangGraph doesn't support 3.9 or older). If
`python3.11 --version` doesn't work yet, install it first — see the repo's
top-level setup notes or:

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-distutils
```

Then, from this folder:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and paste your Groq API key from console.groq.com

python -m app.vectorstore.ingest   # builds the Chroma KB from app/data/kb/*.md
uvicorn app.main:app --reload --port 8000
```

Backend is now live at `http://localhost:8000` — `brightloan-support-ui`'s
Vite dev proxy already points `/chat` there.

## Structure

```
app/
  main.py               FastAPI app, /chat and /health endpoints
  config.py             env var loading (GROQ_API_KEY, model, Chroma path)
  llm.py                Groq chat model factory (langchain-groq)
  state.py              SupportState — shared state passed through the graph
  graph.py              LangGraph wiring: classifier -> rag/handoff/decline -> supervisor
  agents/
    classifier.py       intent classification (03-classifier-agent.md)
    rag_query.py         grounded answers over the policy KB (04-rag-query-agent.md)
    handoff.py            mock support-rep assignment (05-human-handoff-agent.md)
    supervisor.py         groundedness/guardrail review (06-supervisor-guardrails-agent.md)
  vectorstore/
    ingest.py             builds/rebuilds the Chroma collection from app/data/kb/*.md
    store.py               opens the persisted Chroma collection at query time
  data/
    kb/*.md                the static policy content Brightloan "knows"
    roster.json             mock support-rep roster for the handoff agent
```

## Testing it directly (without the frontend)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What documents do I need to apply?", "user_name": "Rajesh"}'
```

Try a handoff trigger too:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to talk to a real person", "user_name": "Rajesh"}'
```

## Current simplifications vs. the full PRD

- No Google-auth session verification yet (`/auth/google`, `/auth/logout`,
  `/chat/history` aren't implemented) — the frontend is in local dev-mode
  sign-in and sends `user_name` directly with each `/chat` call instead of
  relying on a session cookie. See [07-data-model-extensibility.md](../07-data-model-extensibility.md)
  for how real auth slots in later without changing the agent graph.
- `chat_history` is accepted by the state schema but not yet used for
  multi-turn follow-up resolution — each request is treated independently.
- Eval harness and adversarial guardrail tests from
  [08-evaluation-and-testing.md](../08-evaluation-and-testing.md) aren't
  built yet — this is the natural next piece to add.
