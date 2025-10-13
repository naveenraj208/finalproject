# retriever.py
from sklearn.feature_extraction.text import TfidfVectorizer
from db import SessionLocal, MemoryRow
import numpy as np

def _get_rows(conversation_id=None):
    db = SessionLocal()
    if conversation_id:
        rows = db.query(MemoryRow).filter(MemoryRow.conversation_id == conversation_id).all()
    else:
        rows = db.query(MemoryRow).all()
    db.close()
    return rows

def top_k_similar(query, conversation_id=None, k=6):
    rows = _get_rows(conversation_id)
    if not rows:
        return []
    texts = [r.summary or r.text for r in rows]
    # build TF-IDF on the fly (fine for demo / small-scale)
    vec = TfidfVectorizer(stop_words='english')
    try:
        tfidf = vec.fit_transform(texts + [query])
    except ValueError:
        return []
    sims = (tfidf * tfidf.T).toarray()  # cosine-ish for normalized vectors
    # similarity between last vector (query) and documents
    q_sim = sims[-1, :-1]
    idx = np.argsort(-q_sim)[:k]
    results = [(rows[i], float(q_sim[i])) for i in idx if q_sim[i] > 0]
    return results
