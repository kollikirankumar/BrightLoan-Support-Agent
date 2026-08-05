from langchain_core.messages import SystemMessage, HumanMessage

from ..llm import get_llm
from ..logging_config import log_llm_call, logger
from ..state import SupportState
from ..vectorstore.reranker import rerank
from ..vectorstore.store import get_collection

# Two-stage retrieval: cast a wide net with fast embedding search, then
# have the more accurate (but slower) cross-encoder narrow it down to the
# true best matches. See conversation notes on why raw embedding distance
# alone let an irrelevant chunk ("Business Loans...14% APR") outrank the
# genuinely correct one ("Prepayment & Foreclosure") for a percentage-heavy
# query — a cross-encoder reads query+document jointly and doesn't fall
# for that surface-level "contains a number" signal.
RETRIEVAL_TOP_K = 10  # broad, recall-oriented candidate set from Chroma
FINAL_TOP_K = 4         # after re-ranking, how many chunks actually reach the LLM

# Calibrated empirically against cross-encoder/ms-marco-MiniLM-L-6-v2's raw
# score range, across 10 test queries: legitimate matches (including
# "answerable by exclusion" cases, e.g. "do you offer gold loans?" ->
# answered from "Loan Types We Offer") ranged from +9.3 down to about -6.5.
# Genuine misses (totally unrelated questions) clustered tightly around
# -11 to -11.3. -8.5 sits in that gap with margin on both sides.
RERANK_THRESHOLD = -8.5

SYSTEM_PROMPT = """You are Brightloan's support assistant.
Answer the user's question using ONLY the information in the context you
are given in the next message. Do not use any outside knowledge about
loan terms or policy.

If the answer is not fully contained in the context, say so explicitly
instead of guessing — do not extrapolate numbers or policies.

Response style:
- Do not greet the user or use their name — start directly with the answer.
- Keep it compact: 2-4 sentences of plain conversational prose for most
  questions. Do not copy the source's structure, bold text, or bullet
  formatting verbatim — summarize it in your own words.
- Only use a numbered list if the user is specifically asking for an
  ordered, step-by-step process (e.g. "how do I apply"). Everything else
  should be prose, not a list.
- If the user's question about the application process/steps doesn't say
  whether they mean a personal loan or a business loan, and the context
  contains steps for both, answer for both — clearly labeled ("For
  personal loans: ... For business loans: ...") — instead of picking one
  or asking a clarifying question.
"""


def answer_query(state: SupportState) -> SupportState:
    # standalone_query (from the classifier) has follow-up references
    # ("it", "that", "the exact percentage") already resolved using chat
    # history — that's the text that must drive both retrieval and
    # generation, not the raw user_query, which may be ambiguous alone.
    query = state.get("standalone_query") or state["user_query"]

    rid = state.get("request_id", "?")
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=RETRIEVAL_TOP_K)

    documents = results["documents"][0] if results["documents"] else []
    metadatas = results["metadatas"][0] if results["metadatas"] else []
    distances = results["distances"][0] if results.get("distances") else []

    if not documents:
        logger.info(f"[{rid}] RAG found nothing — routing to Handoff Agent")
        return {
            **state,
            "retrieved_chunks": [],
            "citations": [],
            "response_type": "handoff",
        }

    candidate_summary = ", ".join(
        f"{m.get('section')!r} ({d:.3f})" for m, d in zip(metadatas, distances)
    ) or "(none)"
    logger.info(
        f"[{rid}] RAG embedding candidates ({len(documents)}) for {query!r} -> {candidate_summary}"
    )

    scores = rerank(query, documents)
    ranked = sorted(zip(documents, metadatas, scores), key=lambda x: x[2], reverse=True)
    top = ranked[:FINAL_TOP_K]
    documents, metadatas, scores = [list(t) for t in zip(*top)] if top else ([], [], [])

    reranked_summary = ", ".join(
        f"{m.get('section')!r} ({s:.3f})" for m, s in zip(metadatas, scores)
    ) or "(none)"
    logger.info(f"[{rid}] RAG re-ranked top {FINAL_TOP_K} -> {reranked_summary}")

    best_score = scores[0] if scores else None

    if not documents or best_score is None or best_score < RERANK_THRESHOLD:
        logger.info(
            f"[{rid}] RAG best re-rank score {best_score} below threshold "
            f"{RERANK_THRESHOLD} — treating as KB miss, skipping generation, "
            f"routing to Handoff Agent"
        )
        # No draft_response here on purpose — graph.py routes this straight
        # to the real Handoff Agent, which builds the actual message once it
        # knows who the customer is being assigned to.
        return {
            **state,
            "retrieved_chunks": [],
            "citations": [],
            "response_type": "handoff",
        }

    context = "\n\n".join(
        f"[{meta.get('section', meta.get('source_doc', 'KB'))}]\n{doc}"
        for doc, meta in zip(documents, metadatas)
    )

    llm = get_llm(temperature=0.3)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context:\n{context}\n\nUser question: {query}"),
    ]
    response = llm.invoke(messages)
    section_names = [m.get("section") for m in metadatas]
    log_llm_call(
        rid, "rag_query", messages, response.content,
        human_summary=f"query={query!r} + context from sections: {section_names}",
    )
    logger.info(f"[{rid}] RAG draft: {response.content!r}")

    citations = [meta.get("section", meta.get("source_doc")) for meta in metadatas]
    deduped_citations = list(dict.fromkeys(citations))  # preserve order, drop dupes

    return {
        **state,
        "retrieved_chunks": [
            {"content": d, "metadata": m} for d, m in zip(documents, metadatas)
        ],
        "draft_response": response.content,
        "citations": deduped_citations,
        "response_type": "answer",
    }
