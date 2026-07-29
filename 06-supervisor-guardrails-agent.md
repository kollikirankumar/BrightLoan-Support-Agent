# 06 — Supervisor / Guardrails Agent

Parent doc: [README.md](./README.md) | Architecture: [01-architecture.md](./01-architecture.md)

## 1. Purpose

The mandatory final gate every response passes through before reaching the user. This is the component that turns the project from "a chatbot that's usually right" into "a system with an explicit, testable safety layer" — the single most resume-relevant piece of the whole design, since production LLM job postings consistently ask about exactly this (guardrails, eval, groundedness).

## 2. Checks Performed

| # | Check | Type | What it catches |
|---|---|---|---|
| 1 | **Groundedness** | Rule + LLM-judge | RAG agent's answer contains a claim (number, policy detail) not present in the retrieved chunks — i.e. hallucination |
| 2 | **Prohibited content** | Rule (regex/keyword) | Loan approval guarantees ("you're approved"), legal/financial advice beyond scope, discriminatory language |
| 3 | **PII leakage** | Rule | Response accidentally includes another user's data — not reachable in v1 (no real customer DB) but the check is built now so it's active the moment [07](./07-data-model-extensibility.md) lands |
| 4 | **Tone/brand check** | LLM-judge | Response is rude, overly informal, or inconsistent with a financial-services tone |
| 5 | **Escalation triggers** | Rule + sentiment | User expressed frustration ("this is useless", repeated rephrasing of the same question 2+ times), or RAG/classifier confidence was low |

## 3. Implementation: Hybrid Rule + LLM-Judge

Rules run first because they're free and instant — no point spending an LLM call to catch something a regex already caught.

```python
def rule_checks(draft_response: str, retrieved_chunks: list, intent: str) -> list[str]:
    violations = []
    if re.search(r"\b(guarantee|guaranteed|definitely approved)\b", draft_response, re.I):
        violations.append("prohibited_guarantee_language")
    if intent == "account_specific" and "not available" not in draft_response.lower():
        violations.append("account_specific_without_disclaimer")
    return violations
```

If rule checks pass, an LLM-judge call reviews groundedness + tone with structured output:

```
You are reviewing a draft customer support response for Brightloan.
Given the retrieved source context and the draft response, answer:
1. groundedness_ok: true/false — does every factual claim in the draft
   trace to the provided context? List any claim that does not.
2. tone_ok: true/false
3. verdict: "approve" | "revise" | "escalate"
4. notes: brief explanation if not approved

Context: {retrieved_chunks}
Draft response: {draft_response}
```

## 4. Decision Outcomes

| Verdict | Graph routing | Notes |
|---|---|---|
| `approve` | → end, response sent to user | |
| `revise` | → back to RAG Query Agent, once, with `supervisor_notes` injected into its prompt | Max **1** revision cycle — see loop protection below |
| `escalate` | → Human Handoff Agent | Used when revision wouldn't fix the underlying problem (e.g. the KB genuinely doesn't have the answer) |

## 5. Loop Protection

`revision_count` is tracked in shared state. If the Supervisor returns `revise` a second time for the same turn, the graph forces `escalate` regardless of the verdict — this guarantees the graph always terminates in bounded steps and the user is never stuck in a silent retry loop. This is a small but important detail to be able to explain: it's the difference between "a robust agent graph" and "a demo that can infinite-loop under the wrong input."

## 6. Guardrail Rule Examples (starter set — extend during testing)

| Pattern | Category | Action |
|---|---|---|
| "guarantee", "100% approved", "definitely qualify" | Overpromising | Block, force revise |
| Any numeric value not present in `retrieved_chunks` when intent is a static-info category | Hallucination | Block, force revise |
| "legal advice", "tax advice" framed as a recommendation | Scope overreach | Block, force revise with disclaimer instruction |
| User message contains "human", "agent", "call me", "speak to someone" but classifier didn't route to handoff | Missed handoff | Force escalate regardless of RAG draft quality |

## 7. Why This Agent Doesn't Just Re-run the Whole Pipeline

The Supervisor only reviews the **draft + the context it was given** — it doesn't re-do retrieval or re-classify. This keeps it fast (one focused LLM call) and keeps its responsibility narrow and testable in isolation, which is exactly what the eval harness in [08-evaluation-and-testing.md](./08-evaluation-and-testing.md) exploits: you can feed it hand-crafted (draft, context) pairs — including deliberately broken ones — without running the full graph, to check its judgment alone.
