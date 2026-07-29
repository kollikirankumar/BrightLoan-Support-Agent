from sentence_transformers import CrossEncoder

_cross_encoder = None


def get_cross_encoder():
    """Lazy-loaded singleton — cross-encoder/ms-marco-MiniLM-L-6-v2, free,
    runs locally, no API key. Unlike the bi-encoder used for the initial
    Chroma search (query and document embedded independently, compared
    after the fact), a cross-encoder reads the query and each candidate
    document TOGETHER in one pass, so it can catch relevance a bi-encoder
    structurally can't — see 04-rag-query-agent.md for why raw embedding
    distance alone isn't reliable enough as the only retrieval signal.
    """
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def rerank(query: str, documents: list) -> list:
    """Returns a relevance score per document (higher = more relevant),
    in the same order as the input list. Only call this on a short
    candidate list (10-20) — cross-encoders are far too slow to run
    against an entire collection."""
    if not documents:
        return []
    cross_encoder = get_cross_encoder()
    pairs = [(query, doc) for doc in documents]
    return list(cross_encoder.predict(pairs))
