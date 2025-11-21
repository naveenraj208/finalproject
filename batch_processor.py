
import pandas as pd
from memory_manager import MemoryManager

# Initialize MemoryManager
mm = MemoryManager()

# Path to your Excel file
EXCEL_PATH = "smart_city_dataset_500.xlsx"  # change this to your file name

# Read Excel file
df = pd.read_excel(EXCEL_PATH)

# Ensure the required column exists
if "Response" not in df.columns:
    raise ValueError("Excel file must contain a 'Response' column.")

# Insert each response as text into DB
for idx, row in df.iterrows():
    text = str(row["Response"]).strip()
    if text:
        mm.add_memory(text=text)
        print(f"Inserted row {idx+1}")

print("\n✅ All responses inserted successfully!")
