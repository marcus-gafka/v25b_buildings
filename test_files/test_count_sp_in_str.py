import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import TOTAL_STR_CSV

def main():
    print(f"📂 Loading STR CSV: {TOTAL_STR_CSV.name}")
    df = pd.read_csv(TOTAL_STR_CSV)

    if "INDIRIZZO" not in df.columns:
        raise ValueError("❌ ERROR: The CSV does not contain an 'INDIRIZZO' column.")

    # Normalize INDIRIZZO to strings
    df["INDIRIZZO"] = df["INDIRIZZO"].astype(str).str.strip().str.upper()

    # Filter addresses starting with "SAN POLO"
    mask = df["INDIRIZZO"].str.startswith("SAN POLO")
    count = mask.sum()

    print("─────────────────────────────")
    print(f"🔎 Total STR entries in SAN POLO: {count}")
    print("─────────────────────────────")

    # Optional: print all matching rows
    # print(df[mask])

    print("🎉 Done.")

if __name__ == "__main__":
    main()
