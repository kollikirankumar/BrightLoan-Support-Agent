from langgraph.graph import StateGraph, END

from .state import SupportState
from .agents.classifier import classify
from .agents.rag_query import answer_query
from .agents.handoff import assign_rep
from .agents.supervisor import supervise

STATIC_INTENTS = {"loan_process", "offer_amount", "company_policy", "general_faq"}
HANDOFF_INTENTS = {"human_handoff_request", "account_specific"}


def route_after_classify(state: SupportState) -> str:
    intent = state.get("intent")
    if intent == "direct_answer":
        # classify() already set final_text/response_type="meta" directly —
        # chit-chat, assistant identity, glossary terms, personalization,
        # or conversation-meta questions. No KB lookup applies here, so
        # skip straight to supervisor.
        return "supervisor"
    if intent in STATIC_INTENTS:
        return "rag"
    if intent in HANDOFF_INTENTS:
        return "handoff"
    return "decline"


def decline(state: SupportState) -> SupportState:
    return {
        **state,
        "response_type": "decline",
        "draft_response": (
            "I'm focused on Brightloan loan questions and support — "
            "I'm not able to help with that here."
        ),
    }


def route_after_rag(state: SupportState) -> str:
    # RAG sets response_type="handoff" (no draft_response) when retrieval
    # finds nothing — route to the real Handoff Agent instead of the
    # supervisor, so a KB miss still gets a genuine rep assignment and
    # notification, not a canned no-op message.
    if state.get("response_type") == "handoff":
        return "handoff"
    return "supervisor"


def route_after_supervisor(state: SupportState) -> str:
    verdict = state.get("supervisor_verdict", "approve")
    if verdict == "revise":
        return "rag"
    if verdict == "escalate":
        return "handoff"
    return END


def build_graph():
    graph = StateGraph(SupportState)

    graph.add_node("classifier", classify)
    graph.add_node("rag", answer_query)
    graph.add_node("handoff", assign_rep)
    graph.add_node("decline", decline)
    graph.add_node("supervisor", supervise)

    graph.set_entry_point("classifier")
    graph.add_conditional_edges(
        "classifier",
        route_after_classify,
        {"rag": "rag", "handoff": "handoff", "decline": "decline", "supervisor": "supervisor"},
    )
    graph.add_conditional_edges(
        "rag", route_after_rag, {"handoff": "handoff", "supervisor": "supervisor"}
    )
    graph.add_edge("decline", "supervisor")
    graph.add_edge("handoff", "supervisor")
    graph.add_conditional_edges(
        "supervisor", route_after_supervisor, {END: END, "rag": "rag", "handoff": "handoff"}
    )

    return graph.compile()


SUPPORT_GRAPH = build_graph()
