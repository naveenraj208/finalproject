import pandas as pd
from memory_manager import MemoryManager
from llm_client import call_model
from tqdm import tqdm

# -----------------------------
# Configuration
# -----------------------------
INPUT_FILE = "smart_city_dataset_500.xlsx"
CONVERSATION_ID = "smartcity_training"

def import_Responses_to_memory():
    mm = MemoryManager()
    df = pd.read_excel(INPUT_FILE)

    # Determine which column to use
    if "Response" in df.columns:
        column = "Response"
    elif "query" in df.columns:
        column = "query"
    else:
        raise ValueError("❌ Excel must contain a 'Response' or 'query' column.")

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Importing to memory"):
        Response = str(row[column]).strip()
        if not Response:
            continue

        # Generate LLM summary
        try:
            summary = call_model(
                f"Summarize or give short factual insight for: {Response}",
                max_tokens=100,
                temperature=0.0
            )
        except Exception as e:
            summary = f"Error: {e}"

        # Add original Response
        mm.add_memory(
            text=Response,
            conversation_id=CONVERSATION_ID,
            pinned=False,
            importance=1,
            is_longterm=False,
            is_assistant=False
        )

        # Add LLM-generated summary
        mm.add_memory(
            text=summary,
            conversation_id=CONVERSATION_ID,
            pinned=False,
            importance=2,
            is_longterm=True,
            is_assistant=True
        )

    print(f"\n✅ Successfully imported {len(df)} responses into memory.db!")

if __name__ == "__main__":
    import_Responses_to_memory()
