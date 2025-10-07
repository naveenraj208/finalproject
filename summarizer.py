# app/summarizer.py
import re
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

# Load a small deterministic embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

def split_sentences(text: str) -> List[str]:
    """Split text into sentences using regex."""
    return [s.strip() for s in re.split(r'(?<=[.!?]) +', text) if s.strip()]

def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def textrank_summary(text: str, compression_ratio: float = 0.3) -> str:
    """
    Deterministic extractive summarization using cosine similarity TextRank.
    No generation → no hallucination.
    """
    sentences = split_sentences(text)
    if len(sentences) <= 3:
        return text

    embeddings = model.encode(sentences)
    sim = np.dot(embeddings, embeddings.T)
    scores = np.sum(sim, axis=1)
    ranked = np.argsort(scores)[::-1]
    k = max(1, int(len(sentences) * compression_ratio))
    selected = [sentences[i] for i in sorted(ranked[:k])]
    return " ".join(selected)
