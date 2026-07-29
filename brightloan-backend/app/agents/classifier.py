import json
from langchain_core.messages import SystemMessage, HumanMessage

from ..llm import get_llm
from ..logging_config import log_llm_call, logger
from ..state import SupportState

INTENTS = [
    "loan_process", "offer_amount", "company_policy", "general_faq",
    "human_handoff_request", "account_specific", "direct_answer", "out_of_scope",
]

SYSTEM_PROMPT = """You are an intent classifier for Brightloan's customer support system.
You represent Brightloan, a digital lending company offering small-ticket
personal loans and invoice discounting for vendors/suppliers.

Given the recent conversation history and the user's latest message, do
three things:

1. standalone_query: rewrite the latest message into a self-contained
   question that makes sense with NO history at all — resolve pronouns
   and implicit references ("it", "that", "the exact percentage") into
   what they actually refer to, based on the history. If the message is
   already self-contained, or there's no history, just repeat it as-is.
   For direct_answer (see below), just repeat the message as-is.

2. intent: classify the STANDALONE (rewritten) query into exactly one of:
   loan_process, offer_amount, company_policy, general_faq, human_handoff_request, account_specific, direct_answer, out_of_scope

3. answer_text: ONLY when intent is direct_answer — answer the question
   directly and briefly yourself, right now, using the signed-in user's
   name and conversation history you were given below where relevant.
   Leave this empty ("") for every other intent.

Rules:
- account_specific = the user is asking about THEIR OWN existing loan/account
  (status, balance, due date) — not general policy. We do not yet have this
  data connected, so classify it correctly regardless.
- human_handoff_request = the user is asking, right now, to be personally
  connected to a person, or is expressing active frustration wanting
  escalation of their own situation.
- IMPORTANT distinction: a question ABOUT a process (how grievances are
  handled, what the escalation steps are, what happens if a complaint
  isn't resolved) is an INFORMATIONAL question — classify it as
  company_policy or general_faq, NOT human_handoff_request. Only use
  human_handoff_request when the user wants to actually be connected to a
  person themselves, not when they're asking how the process works.
  Example: "What is the process to escalate a complaint?" -> company_policy
  (they're asking about the policy). "I want to escalate my complaint to
  someone" or "Connect me with a manager" -> human_handoff_request (they
  want it to happen now, for themselves).
- direct_answer = ONLY for things that never need Brightloan's specific
  data, and are safe to answer yourself right now:
    - Chit-chat/greetings/thanks ("hi", "thank you", "how are you").
    - Simple questions about the assistant/company's own identity ("what
      is your company name", "who are you", "are you a bot", "what do
      you do"). Answer these confidently and directly — you ARE
      Brightloan's support assistant, a digital lending company. Don't
      hedge or say you don't have the information.
      EXCEPTION: questions about legitimacy, regulation, or trust ("is
      Brightloan legit?", "are you RBI-regulated?", "is this a real
      company?") are NOT simple identity questions — they need the
      actual regulatory details from the KB (About Brightloan document),
      not a shallow "yes". Route these to general_faq instead.
    - Generic financial glossary terms that do NOT depend on Brightloan's
      own numbers or policy ("what does APR mean", "what is a credit
      score", "what is Aadhaar").
    - Personalization/session questions answerable from the signed-in
      user's name given to you below ("who am I", "what's my name").
    - Questions purely about the conversation itself ("what did I just
      ask?", "what are we discussing?", "why did I ask you about?") —
      answer from the history given to you.
- CRITICAL SAFETY RULE: if a question could PLAUSIBLY have a
  Brightloan-specific answer — rates, fees, documents, policies,
  timelines, eligibility, anything a real customer would need our actual
  data for — even if phrased casually, or phrased as a general/evaluative
  question, do NOT use direct_answer. Route it to the matching KB
  category instead (loan_process, offer_amount, company_policy, or
  general_faq). A pure definition of a term ("what does APR mean") is
  direct_answer; a question that asks you to evaluate, compare, or judge
  something against Brightloan's actual numbers ("is 15% a good rate?",
  "is that a lot for a processing fee?", "should I take this loan?") is
  NOT direct_answer, even though it sounds conversational — it needs our
  real numbers to answer honestly, so route it to offer_amount or
  company_policy instead. When in doubt, prefer a KB category over
  direct_answer. Never guess at anything that might be company-specific.
- If ambiguous between two static-info categories, pick the closer one.
- If genuinely unrelated to loans/support and not covered by
  direct_answer above, use out_of_scope.

Respond with ONLY valid JSON, no prose, matching this schema:
{"standalone_query": "...", "intent": "<one of the categories>", "confidence": <0-1 float>, "answer_text": "...", "reasoning": "<one sentence>"}
"""


def _format_history(chat_history):
    if not chat_history:
        return "(no prior messages)"
    return "\n".join(f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in chat_history)


def classify(state: SupportState) -> SupportState:
    llm = get_llm(temperature=0, json_mode=True)
    history_text = _format_history(state.get("chat_history"))
    user_name = state.get("user_name") or "unknown"
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Signed-in user's name: {user_name}\n"
                f"Conversation history:\n{history_text}\n"
                f"Latest message: {state['user_query']}"
            )
        ),
    ]
    response = llm.invoke(messages)
    log_llm_call(state.get("request_id", "?"), "classifier", messages, response.content)

    try:
        parsed = json.loads(response.content)
        intent = parsed.get("intent", "out_of_scope")
        if intent not in INTENTS:
            intent = "out_of_scope"
        confidence = float(parsed.get("confidence", 0.5))
        standalone_query = parsed.get("standalone_query") or state["user_query"]
        answer_text = parsed.get("answer_text") or ""
    except (json.JSONDecodeError, ValueError, TypeError):
        intent, confidence, standalone_query, answer_text = (
            "out_of_scope", 0.0, state["user_query"], "",
        )

    rid = state.get("request_id", "?")
    logger.info(
        f"[{rid}] CLASSIFIER -> intent={intent!r} (conf {confidence}), "
        f"standalone_query={standalone_query!r}"
    )

    result = {
        **state,
        "intent": intent,
        "intent_confidence": confidence,
        "standalone_query": standalone_query,
    }

    if intent == "direct_answer":
        # Answered directly from the classifier's own call — no KB lookup
        # applies here, so this skips RAG/Handoff entirely (see
        # route_after_classify in graph.py) and goes straight to the
        # supervisor as a finished answer (pass-through, no groundedness
        # check needed since there's no retrieved content to check against).
        result["response_type"] = "meta"
        result["final_text"] = answer_text or (
            "I'm not sure how to answer that directly — could you rephrase?"
        )
        logger.info(f"[{rid}] CLASSIFIER answered directly (no KB): {result['final_text']!r}")

    return result
