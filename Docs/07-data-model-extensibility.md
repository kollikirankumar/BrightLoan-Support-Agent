# 07 — Extensibility: Future Existing-Customer Account Data

Parent doc: [README.md](./README.md) | Architecture: [01-architecture.md](./01-architecture.md)

## 1. Purpose of This Document

This is explicitly **not** a v1 build item. It exists so that the v1 architecture can be designed to accommodate real account-specific queries (loan status, EMI due date, outstanding balance) later **without a rewrite** — and so you can talk credibly in an interview about how the system scales, which is often exactly what separates a toy project from one that reads as production-minded.

## 2. The Core Design Principle: Tools, Not Inline Data Access

Every agent that needs external data calls a named tool function; agents never embed data-access logic directly in their prompts or code paths. In v1, exactly one tool exists:

```python
def search_policy_kb(query: str) -> list[Chunk]:
    """RAG Query Agent's only data-access tool."""
```

Adding account-specific support later means adding **one new tool** and **one new agent node** — nothing about the Classifier, RAG Agent, Supervisor, or Handoff Agent needs to change:

```python
def get_customer_loan_status(customer_id: str) -> LoanStatus:
    """Future Account Data Agent's tool. Queries the real customer DB."""
```

## 3. What's Already Reserved in v1 (so nothing breaks when this lands)

- **Classifier taxonomy** already includes `account_specific` as a distinct intent (see [03-classifier-agent.md](./03-classifier-agent.md)) — it's correctly *recognized*, just not yet *served*, today. In v1 it routes to the Human Handoff Agent with an honest "I can't look that up yet" message rather than silently misclassifying into a static-info category and risking a wrong/generic answer.
- **Shared state schema** ([01-architecture.md](./01-architecture.md)) already carries `user_email` from Google Auth on every request — this is the exact field a future lookup needs.
- **Supervisor's PII check** (see [06-supervisor-guardrails-agent.md](./06-supervisor-guardrails-agent.md)) is already active, so the moment real per-customer data enters the graph, there's already a gate checking the response doesn't leak another customer's information.

## 4. Future Data Model (sketch only — not built in v1)

```sql
-- Maps a verified Google identity to an internal customer record.
CREATE TABLE customer_accounts (
  google_email   TEXT PRIMARY KEY,
  customer_id    TEXT NOT NULL,
  kyc_verified   BOOLEAN DEFAULT FALSE,
  linked_at      TIMESTAMP
);

CREATE TABLE loans (
  loan_id         TEXT PRIMARY KEY,
  customer_id     TEXT NOT NULL,
  status          TEXT,          -- 'pending', 'approved', 'disbursed', 'closed'
  principal       DECIMAL,
  outstanding     DECIMAL,
  emi_amount      DECIMAL,
  next_due_date   DATE,
  FOREIGN KEY (customer_id) REFERENCES customer_accounts(customer_id)
);
```

## 5. Future Agent: Account Data Agent (sketch)

Mirrors the RAG Query Agent's structure but queries structured SQL instead of the vector DB, and — critically — requires `kyc_verified = true` and an exact `customer_id` match before returning anything:

```
Classifier: intent = account_specific, user_email from state
    -> lookup customer_id via customer_accounts.google_email
    -> if not found or not kyc_verified: politely explain and route to Human Handoff
    -> if found: get_customer_loan_status(customer_id) -> LoanStatus
    -> generate response grounded in that structured result only
    -> Supervisor's PII/groundedness checks apply exactly as they do today
```

## 6. Security Note for the Future Build (worth stating even though unbuilt)

The moment this lands, the single most important rule is: **the LLM must never receive another customer's row.** The tool function itself — not the LLM — enforces the `customer_id` filter (parameterized query, never string-built from LLM output). This is a standard and important RAG/agent security pattern (never let the model construct raw data-access queries) worth being able to explain even for the parts of the project you didn't build, since it shows you understand the failure mode, not just the happy path.
