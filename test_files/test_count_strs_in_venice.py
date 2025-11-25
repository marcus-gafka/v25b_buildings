import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import FILTERED_STR_CSV

def main():
    print(f"📂 Loading STR CSV: {FILTERED_STR_CSV.name}")
    df = pd.read_csv(FILTERED_STR_CSV)

    if "ADDRESS" not in df.columns:
        raise ValueError("❌ ERROR: The CSV does not contain an 'ADDRESS' column.")

    # Normalize ADDRESS to strings
    df["ADDRESS"] = df["ADDRESS"].astype(str)

    # Filter addresses starting with "X_"
    mask = df["ADDRESS"].str.startswith("X_")
    count = mask.sum()

    print("─────────────────────────────")
    print(f"🔎 Total STR entries starting with 'X_': {count}")
    print("─────────────────────────────")

    # Optional: print all matching rows
    # print(df[mask])

    print("🎉 Done.")

if __name__ == "__main__":
    main()
