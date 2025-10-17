# retriever_faiss.py
import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer

INDEX_PATH = "knowledge.index"
DB_PATH = "kb_meta.db"
EMBED_MODEL = "all-MiniLM-L6-v2"

_model = None
_index = None

def _load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model

def _load_index():
    global _index
    if _index is None:
        _index = faiss.read_index(INDEX_PATH)
    return _index

def _get_text_by_id(fid):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT text FROM kb WHERE id = ?", (str(fid),))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def retrieve(query, top_k=4):
    model = _load_model()
    idx = _load_index()
    emb = model.encode([query], convert_to_numpy=True)
    emb = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12)
    D, I = idx.search(emb.astype('float32'), top_k)
    results = []
    for fid in I[0]:
        if fid == -1: 
            continue
        text = _get_text_by_id(int(fid))
        if text:
            results.append(text)
    return results
