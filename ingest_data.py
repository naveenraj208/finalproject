import os
import pandas as pd
import numpy as np
import faiss
import sqlite3
import uuid
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, FAISS_INDEX_PATH, KB_META_DB_PATH

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

def save_metadata(conn, doc_id, text, metadata=""):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO kb (id, text, metadata) VALUES (?, ?, ?)", (str(doc_id), text, metadata))
    conn.commit()

def ingest_file(file_path, text_column, model, index, conn):
    print(f"Ingesting {file_path}...")
    df = pd.read_excel(file_path)
    texts = df[text_column].astype(str).tolist()
    
    batch_size = 64
    for i in tqdm(range(0, len(texts), batch_size), desc=f"Embedding {os.path.basename(file_path)}"):
        batch_texts = texts[i:i+batch_size]
        embs = model.encode(batch_texts, convert_to_numpy=True)
        
        # Normalize for cosine similarity
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms
        
        # Generate IDs
        ids = []
        for t in batch_texts:
            # FAISS IndexIDMap needs int64 IDs
            new_id = int(uuid.uuid4().int & (2**63 - 1))
            ids.append(new_id)
            save_metadata(conn, new_id, t)
        
        ids = np.array(ids, dtype=np.int64)
        index.add_with_ids(embs.astype('float32'), ids)

def main():
    model = SentenceTransformer(EMBEDDING_MODEL)
    dim = model.get_sentence_embedding_dimension()
    
    # Initialize FAISS Index
    quantizer = faiss.IndexFlatIP(dim)
    index = faiss.IndexIDMap(quantizer)
    
    conn = create_or_open_sqlite(KB_META_DB_PATH)
    
    # Ingest both Excel files
    files_to_ingest = [
        ('smart_city_dataset_500.xlsx', 'Response'),
        ('smart_city_responses.xlsx', 'response')
    ]
    
    for file, col in files_to_ingest:
        if os.path.exists(file):
            ingest_file(file, col, model, index, conn)
        else:
            print(f"Warning: {file} not found.")
            
    # Save FAISS Index
    faiss.write_index(index, FAISS_INDEX_PATH)
    conn.close()
    print(f"Ingestion complete. Index saved to {FAISS_INDEX_PATH}")

if __name__ == "__main__":
    main()
