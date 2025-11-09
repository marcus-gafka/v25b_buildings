import pandas as pd
from constants import ADDRESS_CSV, FILTERED_ADDRESS_CSV

KEEP_FIELDS = [
    "Join_Count",
    "TARGET_FID_12_13",
    "TARGET_FID_1",
    "Full_sesti",
    "Codice_1"
]

def main():
    print("📂 Loading CSV...")
    df = pd.read_csv(ADDRESS_CSV, dtype=str)  # read everything as string

    print("🧹 Filtering fields...")
    df_filtered = df[[f for f in KEEP_FIELDS if f in df.columns]].copy()

    # Convert FID columns to numeric
    df_filtered["TARGET_FID_12_13"] = pd.to_numeric(df_filtered["TARGET_FID_12_13"], errors="coerce").astype("Int64")

    # ✅ Increment all TARGET_FID_12_13 >= 12813 by 1
    mask = df_filtered["TARGET_FID_12_13"] >= 12813
    affected_count = mask.sum()
    if affected_count > 0:
        print(f"🔧 Adjusting {affected_count} FIDs (>= 12813) by +1...")
        df_filtered.loc[mask, "TARGET_FID_12_13"] += 1
    else:
        print("✅ No FIDs >= 12813 found — no adjustment needed.")

    print("🔢 Sorting numerically by TARGET_FID_12_13...")
    df_filtered = df_filtered.sort_values(by=["TARGET_FID_12_13"])

    # Reorder columns: make TARGET_FID_12_13 the first column
    cols = ["TARGET_FID_12_13"] + [c for c in df_filtered.columns if c != "TARGET_FID_12_13"]
    df_filtered = df_filtered[cols]

    print("💾 Saving filtered CSV...")
    df_filtered.to_csv(FILTERED_ADDRESS_CSV, index=False)
    print(f"✅ CSV saved to {FILTERED_ADDRESS_CSV}")

if __name__ == "__main__":
    main()
