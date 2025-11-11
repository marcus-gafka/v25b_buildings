import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
FILTERED_CSV = DATA_DIR / "VPC_Buildings_Filtered.csv"

def main():
    print("📂 Loading filtered CSV...")
    df = pd.read_csv(FILTERED_CSV, dtype=str)

    if "TARGET_FID_12_13" not in df.columns:
        print("❌ Column 'TARGET_FID_12_13' not found.")
        return

    # Try converting FIDs to int safely
    df["TARGET_FID_12_13"] = pd.to_numeric(df["TARGET_FID_12_13"], errors="coerce")
    fids = df["TARGET_FID_12_13"].dropna().astype(int).sort_values().to_list()

    print(f"🔢 Checking {len(fids)} FIDs for sequential order...")
    missing = []
    for i in range(len(fids) - 1):
        expected_next = fids[i] + 1
        if fids[i + 1] != expected_next:
            missing_range = list(range(expected_next, fids[i + 1]))
            missing.extend(missing_range)
            print(f"⚠️ Break between {fids[i]} → {fids[i + 1]} (missing {len(missing_range)})")

    if missing:
        print(f"\n🚨 Found {len(missing)} missing FIDs.")
        print("First few missing:", missing[:20])
    else:
        print("✅ All FIDs are sequential with no gaps.")

if __name__ == "__main__":
    main()
