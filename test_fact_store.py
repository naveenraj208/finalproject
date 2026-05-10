import os
import tempfile
import importlib


def test_fact_store_keeps_conflicts():
    # Isolate storage to a temporary sqlite DB.
    fd, tmp_path = tempfile.mkstemp(prefix="facts_test_", suffix=".db")
    os.close(fd)
    os.environ["FACTS_DB_PATH"] = tmp_path

    import fact_store
    importlib.reload(fact_store)

    # Teach two different values for the same (subject, predicate).
    assert fact_store.detect_and_save_fact("cm of karnataka is sidharamaya") is not None
    assert fact_store.detect_and_save_fact("cm of karnataka is devraj") is not None

    hits = fact_store.search_facts("who is cm of karnataka", top_k=10)
    values = [h["value"] for h in hits]

    assert "sidharamaya" in values
    assert "devraj" in values

    # Re-teach an existing value should not create an extra duplicate.
    fact_store.detect_and_save_fact("cm of karnataka is sidharamaya")
    hits2 = fact_store.search_facts("who is cm of karnataka", top_k=10)
    values2 = [h["value"] for h in hits2]

    assert values2.count("sidharamaya") == 1


if __name__ == "__main__":
    test_fact_store_keeps_conflicts()
    print("✅ test_fact_store_keeps_conflicts passed")

