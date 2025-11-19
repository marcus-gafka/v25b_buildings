import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import ALIAS_CSV

import pandas as pd

# Emoji definitions
EMOJI_SESTIERE = "🏘️"
EMOJI_ISLAND = "🏝️"
EMOJI_BUILDING = "🏠"
EMOJI_TYPE = "🏷️"

OUTPUT_FILE = "data/san_polo_summary.txt"

def main():
    print("📂 Loading building data...")
    df = pd.read_csv(ALIAS_CSV)
    print(f"✅ Loaded {len(df)} total rows\n")

    required_cols = {"Nome_Sesti", "short_alias", "TP_CLS_ED"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # ---- Filter to SAN POLO ----
    df = df[df["Nome_Sesti"].str.strip().str.lower() == "san polo"]

    print(f"🏘️ San Polo rows kept → {len(df)} buildings\n")

    # Extract island codes
    df["island_code"] = df["short_alias"].str[:4]
    df["TP_CLS_ED_clean"] = df["TP_CLS_ED"].fillna("").str.strip()

    islands = sorted(df["island_code"].dropna().unique())
    total_buildings = len(df)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        # ------------------------------
        # HEADER
        # ------------------------------
        f.write(
            f"{EMOJI_SESTIERE}  Sestiere: San Polo\t"
            f"{len(islands)} islands\t{total_buildings} buildings\n\n"
        )

        # ------------------------------
        # PER-ISLAND SUMMARY (quick list)
        # ------------------------------
        for island in islands:
            df_island = df[df["island_code"] == island]
            unique_types = sorted(t for t in df_island["TP_CLS_ED_clean"].unique() if t)

            f.write(
                f"{EMOJI_ISLAND}  {island}:\t"
                f"{EMOJI_BUILDING} {len(df_island)}\t"
                f"{EMOJI_TYPE} {', '.join(unique_types) if unique_types else 'none'}\n"
            )

        # ------------------------------
        # PER-ISLAND TYPE TOTALS (FULL)
        # ------------------------------
        f.write("\n\n🏷️ Building type totals per island:\n\n")

        for island in islands:
            df_island = df[df["island_code"] == island]

            type_counts = df_island["TP_CLS_ED_clean"].value_counts()
            type_list = sorted([t for t in type_counts.index if t])
            max_len = max(len(t) for t in type_list) if type_list else 0

            f.write(f"{EMOJI_ISLAND} {island} — {len(df_island)} buildings\n")

            for t in type_list:
                padded = t + ":" + " " * (max_len - len(t))
                f.write(f"   {EMOJI_TYPE} {padded}  {EMOJI_BUILDING} {type_counts[t]}\n")

            f.write("\n")

    print(f"✅ San Polo summary complete. Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
