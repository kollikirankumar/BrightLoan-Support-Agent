import chromadb
from ..config import CHROMA_PERSIST_DIR, BACKEND_ROOT

_client = None
_collection = None


def get_collection():
    """Opens the persisted Chroma collection built by ingest.py.
    Uses Chroma's default embedding function (all-MiniLM-L6-v2 via
    onnxruntime) — same model the PRD specifies, lighter runtime than
    pulling in sentence-transformers/torch directly.
    """
    global _client, _collection
    if _collection is None:
        persist_path = BACKEND_ROOT / CHROMA_PERSIST_DIR
        _client = chromadb.PersistentClient(path=str(persist_path))
        _collection = _client.get_or_create_collection("policy_kb")
    return _collection
