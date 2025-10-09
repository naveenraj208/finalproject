# evaluate.py
import sqlite3, matplotlib.pyplot as plt

conn = sqlite3.connect("memory_store.db")
cur = conn.cursor()
cur.execute("SELECT COUNT(*), SUM(tokens) FROM messages")
msgs, total_tokens = cur.fetchone()
cur.execute("SELECT COUNT(*), SUM(tokens) FROM summaries")
sums, sum_tokens = cur.fetchone()
conn.close()

compression = total_tokens / max(sum_tokens + total_tokens, 1)
print(f"Compression Ratio: {compression:.2f}")

plt.bar(["Messages", "Summaries"], [total_tokens, sum_tokens])
plt.title("Token Distribution")
plt.ylabel("Tokens")
plt.show()
