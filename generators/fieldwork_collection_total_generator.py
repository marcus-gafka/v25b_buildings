import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import TOTAL_FIELDWORK_CSV, FIELDWORK_DIR

import pandas as pd
import re

FILE_PATTERN = re.compile(r"^[A-Z]{2}-[A-Z0-9]{4}-F\.csv$", re.IGNORECASE)

def main():
    all_dfs = []

    print(f"📁 Scanning directory: {FIELDWORK_DIR}")

    # === Loop through all matching files ===
    for file_path in FIELDWORK_DIR.iterdir():
        if file_path.is_file() and FILE_PATTERN.match(file_path.name):
            print(f"📂 Loading {file_path.name}...")
            df = pd.read_csv(file_path)
            all_dfs.append(df)

    if not all_dfs:
        print("⚠️ No matching files found.")
        return

    # === Concatenate all DataFrames ===
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # === Save combined CSV ===
    combined_df.to_csv(TOTAL_FIELDWORK_CSV, index=False)
    print(f"\n💾 Saved combined CSV: {TOTAL_FIELDWORK_CSV}")
    print(f"✅ Total rows: {len(combined_df)}")

if __name__ == "__main__":
    main()
