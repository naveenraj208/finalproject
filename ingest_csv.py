# ingest_csv.py
import os
import argparse
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import sqlite3
import uuid
from tqdm import tqdm

# macOS safety: run this script directly (not imported) to avoid uvicorn multiprocessing issues.
# Usage: python ingest_csv.py --csv data.csv --index knowledge.index --db kb_meta.db --model all-MiniLM-L6-v2 --batch 64

def create_or_open_sqlite(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS kb (
        id TEXT PRIMARY KEY,
        text TEXT,
        metadata TEXT
    )
    """)
    conn.commit()
    return conn

def save_metadata(conn, uuid_str, text, metadata=""):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO kb (id, text, metadata) VALUES (?, ?, ?)", (uuid_str, text, metadata))
    conn.commit()

def main(csv_path, index_path, db_path, model_name, batch_size):
    df = pd.read_csv(csv_path)
    if 'text' not in df.columns and ('question' not in df.columns or 'answer' not in df.columns):
        raise ValueError("CSV must contain 'text' column or 'question' and 'answer' columns.")

    # Choose a text column: prefer a combined question+answer summary
    if 'text' in df.columns:
        texts = df['text'].astype(str).tolist()
    else:
        texts = (df['question'].astype(str) + "\n\n" + df['answer'].astype(str)).tolist()

    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()

    # Create / load FAISS index
    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        # we'll append; index dimension should match
        if index.d != dim:
            raise ValueError("Existing index dimension mismatch.")
    else:
        index = faiss.IndexFlatIP(dim)  # use inner product on normalized vectors (we'll normalize)
        # (optionally wrap IndexFlatIP with faiss.IndexIDMap to store ids)
        index = faiss.IndexIDMap(index)

    conn = create_or_open_sqlite(db_path)

    # Embedding & add in batches
    id_list = []
    start = 0
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch_texts = texts[i:i+batch_size]
        embs = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False, batch_size=batch_size)
        # normalize for cosine via inner product
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms==0] = 1.0
        embs = embs / norms

        # generate integer ids for FAISS and save mapping in sqlite
        ids = []
        for t in batch_texts:
            u = str(uuid.uuid4())
            ids.append(int(uuid.uuid4().int & (2**63-1)))  # produce a 63-bit positive integer id for faiss
            # store mapping: we'll use sqlite to map faiss id -> uuid -> text
            save_metadata(conn, str(ids[-1]), t, "")
        ids = np.array(ids, dtype=np.int64)

        index.add_with_ids(embs.astype('float32'), ids)

    # Save index
    faiss.write_index(index, index_path)
    conn.close()
    print("Ingestion complete. Index saved to", index_path, "DB saved to", db_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", dest="csv", required=True)
    parser.add_argument("--index", dest="index", default="knowledge.index")
    parser.add_argument("--db", dest="db", default="kb_meta.db")
    parser.add_argument("--model", dest="model", default="all-MiniLM-L6-v2")
    parser.add_argument("--batch", dest="batch", type=int, default=64)
    args = parser.parse_args()
    main(args.csv, args.index, args.db, args.model, args.batch)
