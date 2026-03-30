import os
import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer
from db import SessionLocal, MemoryRow
from config import EMBEDDING_MODEL, FAISS_INDEX_PATH, KB_META_DB_PATH

# Load model once
_model = SentenceTransformer(EMBEDDING_MODEL)

def get_embeddings(texts):
    if isinstance(texts, str):
        texts = [texts]
    embs = _model.encode(texts, convert_to_numpy=True)
    # Normalize for cosine similarity (Inner Product on normalized vectors)
    norms = np.linalg.norm(embs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (embs / norms).astype('float32')

def _get_rows(conversation_id=None):
    db = SessionLocal()
    if conversation_id:
        rows = db.query(MemoryRow).filter(MemoryRow.conversation_id == conversation_id).all()
    else:
        rows = db.query(MemoryRow).all()
    db.close()
    return rows

def top_k_similar(query, conversation_id=None, k=6):
    """
    Search in conversational memory (STM/LTM) using brute-force cosine similarity (for small scale).
    """
    rows = _get_rows(conversation_id)
    if not rows:
        return []
    
    q_emb = get_embeddings(query)
    doc_texts = [r.summary or r.text for r in rows]
    doc_embs = get_embeddings(doc_texts)
    
    # Cosine similarity is just dot product since they are normalized
    scores = np.dot(doc_embs, q_emb.T).flatten()
    
    idx = np.argsort(-scores)[:k]
    results = [(rows[i], float(scores[i])) for i in idx if scores[i] > 0]
    return results

def search_knowledge_base(query, k=3):
    """
    Search in the external Knowledge Base using FAISS index.
    """
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(KB_META_DB_PATH):
        return []
    
    try:
        index = faiss.read_index(FAISS_INDEX_PATH)
        q_emb = get_embeddings(query)
        
        # Search FAISS
        distances, ids = index.search(q_emb, k)
        
        # Retrieve metadata from sqlite
        results = []
        conn = sqlite3.connect(KB_META_DB_PATH)
        cursor = conn.cursor()
        for doc_id, dist in zip(ids[0], distances[0]):
            if doc_id == -1: continue
            cursor.execute("SELECT text FROM kb WHERE id = ?", (str(doc_id),))
            row = cursor.fetchone()
            if row:
                results.append((row[0], float(dist)))
        conn.close()
        return results
    except Exception as e:
        print(f"KB Search Error: {e}")
        return []
