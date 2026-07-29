# 03 — Classifier Agent

Parent doc: [README.md](./README.md) | Architecture: [01-architecture.md](./01-architecture.md)

## 1. Purpose

The first node every query hits. Its only job is to figure out **what the customer wants** and **who should handle it** — it never answers the question itself. Keeping classification and answering strictly separate is what makes each agent independently testable (see [08-evaluation-and-testing.md](./08-evaluation-and-testing.md)) and what makes the routing logic auditable.

## 2. Intent Taxonomy

| Intent | Example queries | Routes to |
|---|---|---|
| `loan_process` | "How do I apply?", "What documents do I need?", "How long does approval take?" | RAG Query Agent |
| `offer_amount` | "What's the maximum I can borrow?", "What are your interest rates?" | RAG Query Agent |
| `company_policy` | "What's your prepayment penalty?", "Can I get a co-applicant?" | RAG Query Agent |
| `general_faq` | Anything static/informational not covered above | RAG Query Agent |
| `human_handoff_request` | "I want to talk to someone", "Can you call me?", "This isn't helping" | Human Handoff Agent |
| `account_specific` *(reserved, stubbed)* | "What's my EMI due date?", "Has my loan been approved?" | Human Handoff Agent (with a "not available yet" framing — see [07](./07-data-model-extensibility.md)) |
| `out_of_scope` | Anything unrelated to loans/support (weather, general chit-chat, unrelated product questions) | Polite Decline node |

## 3. Input / Output Schema

**Input** (from shared state): `user_query: str`, `chat_history: list[dict]` (for resolving follow-ups like "what about for that one").

**Output** (written back to shared state):

```json
{
  "intent": "offer_amount",
  "intent_confidence": 0.93,
  "extracted_entities": {
    "loan_type": "personal",
    "mentions_amount": true
  },
  "reasoning": "User is asking about maximum borrowing limit for a personal loan."
}
```

The classifier is prompted to **always** return this structured JSON (via the LLM's structured-output/JSON mode) — never free text. This keeps the graph's conditional routing deterministic code, not another LLM call.

## 4. Prompt Design

System prompt sketch:

```
You are an intent classifier for Brightloan's customer support system.
Classify the user's message into exactly one of these categories:
[loan_process, offer_amount, company_policy, general_faq,
 human_handoff_request, account_specific, out_of_scope]

Rules:
- account_specific = the user is asking about THEIR OWN existing loan/account
  (status, balance, due date) — not general policy. We do not yet have this
  data connected, so classify it correctly regardless.
- human_handoff_request = the user explicitly asks for a person, phone call,
  or expresses frustration/wants escalation.
- If the message is ambiguous between two static-info categories
  (loan_process vs company_policy), pick the closer one — RAG retrieval
  will pull from the right document regardless of which static category wins.
- If genuinely unrelated to loans/support, use out_of_scope.

Return JSON only, matching the provided schema. Include a one-sentence
"reasoning" field explaining your choice.
```

Few-shot examples (3-5 per category) are included in the prompt — small classification tasks like this benefit far more from good examples than from a longer instruction paragraph.

## 5. Ambiguity & Multi-Intent Handling

- **Multiple static-info sub-intents in one message** ("what's the max loan and what documents do I need") — not a problem worth splitting; all four static categories route to the same RAG agent, so a single classification of, say, `loan_process` is enough; the RAG agent's retrieval step naturally pulls chunks covering both sub-questions.
- **Static question + handoff request together** ("what's the interest rate, and also can someone call me") — classify as `human_handoff_request` (handoff takes priority when explicitly requested) but pass the full original query into `extracted_entities.original_query` so the assigned rep sees the actual question, not just "wants a call."
- **Low confidence** (`intent_confidence < 0.6`): route to a lightweight clarifying-question response ("Just to make sure I get you the right info — are you asking about interest rates or the application process?") rather than guessing. This is cheap to implement (a simple threshold check after the classifier node) and is a legitimate guardrail-adjacent design point worth calling out in an interview.

## 6. Why This Node Doesn't Use RAG or Call the KB

Classification is a closed-set labeling task over the *user's message*, not a knowledge-retrieval task — it doesn't need policy documents to decide "this is an `offer_amount` question." Keeping it retrieval-free makes it fast (single small LLM call, no vector search) and keeps the separation of concerns clean: classifier decides *what kind of question*, RAG agent decides *what the answer is*.
