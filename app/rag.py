"""RAG over policy documents (ChromaDB)."""
import os

import chromadb
from chromadb.utils import embedding_functions

from app import config


def _collection():
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=config.OPENAI_API_KEY, model_name=config.EMBED_MODEL)
    return client.get_or_create_collection("policies", embedding_function=ef)


def _chunks(text, max_chars=600):
    out, cur = [], ""
    for para in text.split("\n\n"):
        if len(cur) + len(para) > max_chars and cur:
            out.append(cur.strip())
            cur = ""
        cur += para + "\n\n"
    if cur.strip():
        out.append(cur.strip())
    return out


def ingest():
    col = _collection()
    for fn in sorted(os.listdir(config.POLICY_DIR)):
        if not fn.endswith((".md", ".txt")):
            continue
        with open(os.path.join(config.POLICY_DIR, fn), encoding="utf-8") as f:
            chunks = _chunks(f.read())
        col.upsert(ids=[f"{fn}-{i}" for i in range(len(chunks))], documents=chunks,
                   metadatas=[{"source": fn}] * len(chunks))
        print(f"[rag] indexed {fn}: {len(chunks)} chunks")


def search(question, k=3):
    col = _collection()
    res = col.query(query_texts=[question], n_results=k)
    return [{"source": m["source"], "text": d}
            for d, m in zip(res["documents"][0], res["metadatas"][0])]


if __name__ == "__main__":
    ingest()
