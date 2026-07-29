# 04 — RAG Query Agent

Parent doc: [README.md](./README.md) | Architecture: [01-architecture.md](./01-architecture.md)

## 1. Purpose

Answers the four static-data intents (`loan_process`, `offer_amount`, `company_policy`, `general_faq`) using **only** information retrieved from the company's actual policy documents. This is the agent the whole project's purpose hinges on: it must never state a number, rate, or policy that isn't traceable to a source document.

## 2. Knowledge Base Content (v1, static)

Since there's no real company backing this project, author a small set of realistic policy documents yourself — this is part of the deliverable, not a placeholder to skip:

| Document | Contents |
|---|---|
| `loan_process.md` | Application steps, required documents (ID proof, income proof, bank statements), typical approval timeline, eligibility criteria |
| `offer_terms.md` | Loan amount ranges by category (e.g. personal/business), interest rate ranges, tenure options, processing fees |
| `company_policy.md` | Prepayment/foreclosure policy, late payment policy, co-applicant rules, cancellation policy |
| `faq.md` | Miscellaneous — "can I apply if self-employed", "what happens if I miss an EMI", etc. |

Write these as clean markdown with clear headings — the heading structure becomes chunk metadata (see below), and realistic-but-fictional numbers are fine (e.g. "personal loans: ₹50,000–₹5,00,000, 11–18% p.a."). Keep every number consistent across documents; the eval harness will check that answers match these source values exactly.

## 3. Ingestion Pipeline

```
Markdown docs --> chunker --> embedder --> Chroma collection
```

| Step | Choice | Detail |
|---|---|---|
| Chunking | Recursive character/markdown-header splitter | Chunk size ~300-500 tokens, 50-token overlap; split on markdown headers first so a chunk never straddles two unrelated policy sections |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (local, free, no API quota used) | Keeps embedding cost off the Groq/Gemini free-tier budget, which you want reserved for generation calls |
| Vector DB | Chroma, persisted to local disk in the backend container | Collection name: `policy_kb` |
| Metadata per chunk | `{ "source_doc": "offer_terms.md", "section": "Personal Loan Rates", "last_updated": "2026-07-01" }` | Metadata is what makes citations possible in the UI |

Re-ingestion is a manual script (`ingest.py`) run whenever the source markdown changes — no need for a live-sync pipeline at this scale.

## 4. Retrieval

- `top_k = 4` similarity search against the query embedding.
- Optional: MMR (max marginal relevance) instead of plain top-k if early testing shows retrieved chunks are too redundant (e.g. all 4 chunks from the same section).
- Similarity threshold: if the top chunk's score is below a set cutoff, treat retrieval as **failed** rather than force-feeding a weak match — this triggers the "not found in KB" fallback (§6), not a guess.

## 5. Answer Generation

Prompt template (sketch):

```
You are Brightloan's support assistant, speaking with {user_name}.
Answer the user's question using ONLY the information in the context
below. Do not use any outside knowledge about loans or interest rates.

If the answer is not fully contained in the context, say so explicitly
instead of guessing — do not extrapolate numbers or policies.

Context:
{retrieved_chunks_with_source_labels}

User question: {user_query}

Respond conversationally, addressing {user_name} by name naturally
(not in every sentence). After your answer, list the source section(s)
you used.
```

Output includes a `citations: list[str]` field (source doc + section) written back to shared state — this is what the frontend's citation pill (see [02](./02-frontend-react-auth.md)) renders, and what the Supervisor Agent's groundedness check (see [06](./06-supervisor-guardrails-agent.md)) verifies against.

## 6. Fallback Behavior

| Situation | Behavior |
|---|---|
| Retrieval score below threshold | Respond: "I don't have that specific information — let me connect you with someone who can help," and set a flag that routes to the Human Handoff Agent instead of guessing. |
| Supervisor flags the draft as ungrounded (hallucinated detail not in the retrieved chunks) | Draft is sent back to this agent once for revision with the supervisor's specific objection; if still ungrounded, escalate to Human Handoff. |
| Query intent was `account_specific` but somehow reached this agent (shouldn't happen given the classifier, but defensive) | Explicit refusal + handoff — see [07](./07-data-model-extensibility.md). |

## 7. Personalization

The agent has `user_name` in its context (from Google Auth via shared state) and is instructed to use it naturally, not mechanically — the prompt explicitly says "not in every sentence" to avoid the stilted "Hello Rajesh! Rajesh, your answer is..." failure mode that's an easy tell of an under-designed prompt.
