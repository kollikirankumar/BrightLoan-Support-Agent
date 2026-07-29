# 05 — Human Handoff Agent

Parent doc: [README.md](./README.md) | Architecture: [01-architecture.md](./01-architecture.md)

## 1. Purpose

Connects a customer to a **specific, named real person** when: (a) the customer explicitly asks for a human, (b) the RAG agent's retrieval failed or was flagged ungrounded, or (c) the query falls under the reserved `account_specific` intent that isn't wired to real data yet. "Assign one real person" is the operative requirement — the output must never be a generic "our team will contact you," since that's not meaningfully different from a form submission and doesn't demonstrate any agentic reasoning.

## 2. Support Roster (mock data model)

Since there's no real support team, model a small static roster — 4-6 reps is enough to demonstrate matching logic:

```json
// support_roster.json
[
  {
    "id": "rep_001",
    "name": "Priya Sharma",
    "specialty": ["loan_process", "general_faq"],
    "available_slots": ["Today 3:30 PM", "Today 5:00 PM", "Tomorrow 10:00 AM"],
    "status": "active"
  },
  {
    "id": "rep_002",
    "name": "Arjun Mehta",
    "specialty": ["offer_amount", "company_policy"],
    "available_slots": ["Today 4:00 PM", "Tomorrow 11:30 AM"],
    "status": "active"
  }
]
```

In v1 this is a JSON file or a single SQLite table — no need for a real HR system integration.

## 3. Assignment Algorithm

```
1. Read intent (and original sub-question, if handoff was itself the intent)
   from shared state to determine the needed specialty.
2. Filter roster to reps where specialty matches AND status == "active".
3. If no specialty match, fall back to any active rep (a general queue).
4. Among matches, pick by: fewest slots already booked in this session
   (simple round-robin proxy) -> earliest available slot.
5. "Book" the first available slot (mark it consumed for this demo session).
6. Write a HandoffRequest record.
```

This is intentionally simple (round-robin + specialty filter, not a real scheduling optimizer) — the point for this project is demonstrating an agent that takes a concrete, verifiable **action** (an assignment with a record), not building a scheduling engine.

## 4. Handoff Record

```json
{
  "handoff_id": "ho_8841",
  "customer_name": "Rajesh",
  "customer_email": "rajesh@example.com",
  "original_query": "What's the max loan amount for a business loan?",
  "assigned_rep": { "id": "rep_002", "name": "Arjun Mehta" },
  "scheduled_slot": "Today 4:00 PM",
  "status": "confirmed",
  "created_at": "2026-07-25T11:40:00Z"
}
```

Persisted to SQLite so it survives a page refresh within the demo and gives you a real "database" to show in a walkthrough.

## 5. Output to the User

Written to shared state as a structured object (not just text), so the frontend renders the dedicated `<HandoffCard>` (see [02](./02-frontend-react-auth.md)) rather than a plain chat bubble:

```json
{
  "type": "handoff",
  "rep_name": "Arjun Mehta",
  "rep_specialty": "Loan Offers & Policy",
  "scheduled_slot": "Today 4:00 PM",
  "message": "I've connected you with Arjun Mehta, our loan offers specialist. He's available today at 4:00 PM — you'll see a confirmation with a call link shortly."
}
```

The "call link" is a mock placeholder (e.g. a static Google Meet-style URL string) — real telephony/calendar wiring is explicitly future scope (§7).

## 6. When This Agent Is Invoked

| Trigger | Source |
|---|---|
| Explicit request | Classifier routes `human_handoff_request` directly here |
| RAG retrieval failure | RAG agent sets a flag; graph edge routes here instead of Supervisor |
| Guardrail escalation | Supervisor Agent verdict = `escalate` (see [06](./06-supervisor-guardrails-agent.md)) |
| Reserved account-specific intent | Classifier routes `account_specific` here with a "not available yet" framing (see [07](./07-data-model-extensibility.md)) — the message explains the limitation honestly rather than pretending to look it up |

## 7. Future Extension (explicitly out of scope for v1)

- Real calendar integration: Google Calendar API to check actual rep availability and create a real event.
- Real notification: email/SMS confirmation via a provider like Twilio or SendGrid (both have limited free tiers, easy to add later without touching the assignment logic above).
- Real-time handoff: instead of async scheduling, live chat handoff to a human agent dashboard (would require a second, human-facing UI — a natural v2 feature to mention as "designed for but not built").
