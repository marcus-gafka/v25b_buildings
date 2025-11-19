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

OUTPUT_FILE = "data/buildings_summary.txt"

def main():
    print("📂 Loading building data...")
    df = pd.read_csv(ALIAS_CSV)
    print(f"✅ Loaded {len(df)} total rows\n")

    required_cols = {"Nome_Sesti", "short_alias", "TP_CLS_ED"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    df["island_code"] = df["short_alias"].str[:4]
    df["TP_CLS_ED_clean"] = df["TP_CLS_ED"].fillna("").str.strip()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        # -------- PER-SESTIERE SECTION --------
        for sestiere, group in df.groupby("Nome_Sesti"):

            islands = sorted(group["island_code"].dropna().unique())
            total_buildings = len(group)

            # Header
            f.write(f"{EMOJI_SESTIERE}  Sestiere: {sestiere}\t{len(islands)} islands\t{total_buildings} buildings\n\n")

            # --- Island list ---
            for island in islands:
                df_island = group[group["island_code"] == island]
                unique_types = sorted(t for t in df_island["TP_CLS_ED_clean"].unique() if t)

                f.write(
                    f"\t{EMOJI_ISLAND}  {island}:\t"
                    f"{EMOJI_BUILDING} {len(df_island)}\t"
                    f"{EMOJI_TYPE} {', '.join(unique_types) if unique_types else 'none'}\n"
                )

            f.write("\n")

            # --- PER-SESTIERE TYPE TOTALS ---
            f.write(f"🏷️ Total building types in {sestiere}:\n")

            type_counts = group["TP_CLS_ED_clean"].value_counts()
            type_list = sorted([t for t in type_counts.index if t])
            max_len = max(len(t) for t in type_list) if type_list else 0

            for t in type_list:
                padded_type = t + ":" + " " * (max_len - len(t))  # colon before padding
                f.write(f"  {EMOJI_TYPE} {padded_type}  {EMOJI_BUILDING} {type_counts[t]}\n")

            f.write("\n\n")  # end of sestiere

    print(f"✅ Summary complete. Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
