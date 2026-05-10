# fact_store.py
"""
Dedicated persistent fact store for Synthaura Prime.
When a user teaches the AI a fact (e.g. "the MLA of Chepauk is Udhayanidhi Stalin"),
it is saved here. On future queries the AI retrieves and cites it from the DB.
"""
import os
import sqlite3
import re
from datetime import datetime

DB_PATH = os.environ.get("FACTS_DB_PATH", "facts.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            value TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


_init_db()


def save_fact(subject: str, predicate: str, value: str, raw_text: str):
    """
    Save a taught fact.

    We intentionally DO NOT upsert (overwrite) conflicting values for the same
    (subject, predicate). This allows returning both X and Y when users
    teach different versions over time.
    """
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    subject_n = subject.lower().strip()
    predicate_n = predicate.lower().strip()
    value_n = value.strip()

    # Avoid exact duplicates, but allow conflicts (same subject+predicate with different value).
    existing_same = conn.execute(
        "SELECT id FROM facts WHERE LOWER(subject)=? AND LOWER(predicate)=? AND LOWER(value)=?",
        (subject_n, predicate_n, value_n.lower())
    ).fetchone()

    if not existing_same:
        conn.execute(
            "INSERT INTO facts (subject, predicate, value, raw_text, created_at) VALUES (?,?,?,?,?)",
            (subject_n, predicate_n, value_n, raw_text.strip(), now)
        )
    conn.commit()
    conn.close()


def search_facts(query: str, top_k: int = 5) -> list[dict]:
    """
    Search facts by matching query keywords against subject, predicate, value.
    Returns list of matching fact dicts.
    """
    conn = _get_conn()
    # tokenize query into meaningful words (ignore stop words)
    stop_words = {"who", "is", "the", "of", "are", "what", "a", "an", "in", "for", "at", "?", "which", "tell", "me"}
    # Include short tokens like "cm" that are still important for fact matching.
    words = [w.lower().strip("?.,!") for w in query.split() if w.lower().strip("?.,!") not in stop_words and len(w) >= 2]

    if not words:
        conn.close()
        return []

    conditions = " OR ".join(["(LOWER(subject) LIKE ? OR LOWER(predicate) LIKE ? OR LOWER(value) LIKE ?)"] * len(words))
    params = []
    for w in words:
        params.extend([f"%{w}%", f"%{w}%", f"%{w}%"])

    rows = conn.execute(
        f"SELECT * FROM facts WHERE {conditions} ORDER BY created_at DESC LIMIT ?",
        params + [top_k]
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_facts() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM facts ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Teaching Detection ────────────────────────────────────────────────────────

# Question words — if any are present, it's a query, NOT a teaching statement
QUESTION_WORDS = {"who", "what", "which", "where", "when", "how", "why", "whose", "whom"}

# Patterns like:
#   "the MLA of Chepauk is Udhayanidhi Stalin"
#   "cm of karnataka is sidharamaya"
#   "India's capital is New Delhi"
#   "chennai mayor is xyz"
TEACH_PATTERNS = [
    # "the <predicate> of <subject> is <value>"
    re.compile(
        r"^the\s+(?P<predicate>[\w\s]{2,30}?)\s+of\s+(?P<subject>[\w\s]{2,30}?)\s+is\s+(?P<value>.+)$",
        re.IGNORECASE
    ),
    # "<predicate> of <subject> is <value>"  — no "the" needed (e.g. "cm of karnataka is ...")
    re.compile(
        r"^(?P<predicate>[\w\s]{2,40}?)\s+of\s+(?P<subject>[\w\s]{2,30}?)\s+is\s+(?P<value>.+)$",
        re.IGNORECASE
    ),
    # "<subject>'s <predicate> is <value>"
    re.compile(
        r"^(?P<subject>[\w\s]{2,30}?)'s\s+(?P<predicate>[\w\s]{2,30}?)\s+is\s+(?P<value>.+)$",
        re.IGNORECASE
    ),
    # "<subject> is <value>"  — safe catch-all (e.g. "chennai mayor is xyz")
    re.compile(
        r"^(?P<subject>[\w\s]{3,40}?)\s+is\s+(?P<value>[\w\s]{2,60})$",
        re.IGNORECASE
    ),
]


def detect_and_save_fact(text: str) -> dict | None:
    """
    Try to extract a fact from user text. If found, save it and return the fact dict.
    Returns None if no teachable fact detected.
    """
    text = text.strip().rstrip(".")

    # Reject questions immediately
    if text.endswith("?"):
        return None
    first_word = text.split()[0].lower() if text.split() else ""
    if first_word in QUESTION_WORDS:
        return None
    # Reject if any question word appears near the start (first 3 words)
    first_three = {w.lower() for w in text.split()[:3]}
    if first_three & QUESTION_WORDS:
        return None

    for pattern in TEACH_PATTERNS:
        m = pattern.match(text)
        if m:
            groups = m.groupdict()
            subject = groups.get("subject", "").strip()
            predicate = groups.get("predicate", "is").strip()
            value = groups.get("value", "").strip()

            # Value must be non-trivial (at least 2 characters)
            if not value or len(value) < 2:
                continue
            # Value must not start with a question word
            if value.split()[0].lower() in QUESTION_WORDS:
                continue
            # Avoid saving first-person statements
            skip_subjects = {"i", "my name", "he", "she", "it", "they", "you", "we"}
            if subject.lower() in skip_subjects:
                continue

            save_fact(subject, predicate, value, raw_text=text)
            return {"subject": subject, "predicate": predicate, "value": value}

    return None
