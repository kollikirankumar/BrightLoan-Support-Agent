"""Rebuilds the policy_kb Chroma collection from app/data/kb/*.md.

Run this whenever the KB markdown changes:
    python -m app.vectorstore.ingest
"""
import re
import chromadb

from ..config import CHROMA_PERSIST_DIR, BACKEND_ROOT

KB_DIR = BACKEND_ROOT / "app" / "data" / "kb"


def chunk_markdown(text: str, fallback_title: str):
    """Splits on H2 (##) headers so each chunk is one coherent policy
    section — matches the ingestion design in 04-rag-query-agent.md."""
    sections = re.split(r"\n(?=## )", text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        title_match = re.match(r"^##\s+(.+)", section)
        if title_match:
            title = title_match.group(1)
        else:
            # Content before the first ## header — normally just the
            # "# Title" line. A bare title with no real body embeds too
            # generically and can outrank genuinely relevant chunks for
            # vague queries, so skip it unless there's substantive
            # content beyond the title itself.
            body = re.sub(r"^#\s+.+", "", section).strip()
            if not body:
                continue
            title = fallback_title
        chunks.append({"content": section, "section": title})
    return chunks


def main():
    persist_path = BACKEND_ROOT / CHROMA_PERSIST_DIR
    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection("policy_kb")

    existing = collection.get()
    if existing["ids"]:
        collection.delete(ids=existing["ids"])

    ids, documents, metadatas = [], [], []
    md_files = sorted(KB_DIR.glob("*.md"))
    for md_file in md_files:
        text = md_file.read_text()
        for i, chunk in enumerate(chunk_markdown(text, md_file.stem)):
            ids.append(f"{md_file.stem}-{i}")
            documents.append(chunk["content"])
            metadatas.append({"source_doc": md_file.name, "section": chunk["section"]})

    if not ids:
        print(f"No markdown files found in {KB_DIR}")
        return

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Ingested {len(ids)} chunks from {len(md_files)} documents into {persist_path}")


if __name__ == "__main__":
    main()
