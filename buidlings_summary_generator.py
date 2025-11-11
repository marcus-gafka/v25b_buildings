import pandas as pd
from constants import ALIAS_CSV

# Emoji definitions
EMOJI_SESTIERE = "🏘️"  # for sestiere
EMOJI_ISLAND = "🏝️"    # for island
EMOJI_BUILDING = "🏠"   # for building
EMOJI_TYPE = "🏷️"      # for building type

# Output file
OUTPUT_FILE = "data/buildings_summary.txt"

def main():
    print("📂 Loading building data...")
    df = pd.read_csv(ALIAS_CSV)
    print(f"✅ Loaded {len(df)} total rows\n")

    # Ensure necessary columns exist
    required_cols = {"Nome_Sesti", "short_alias", "TP_CLS_ED"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Missing required columns: {missing}")

    # Extract island codes (first 4 chars of short_alias)
    df["island_code"] = df["short_alias"].str[:4]

    # Clean building types for display (remove blanks only for types, not rows)
    df["TP_CLS_ED_clean"] = df["TP_CLS_ED"].fillna("").str.strip()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        # Group by sestiere
        for sestiere, group in df.groupby("Nome_Sesti"):
            islands = sorted(group["island_code"].dropna().unique())
            total_buildings = len(group)
            
            # Sestiere header
            f.write(f"{EMOJI_SESTIERE}  Sestiere: {sestiere}\t{len(islands)} islands\t{total_buildings} buildings\n\n")
            
            # Island-level info
            for island in islands:
                df_island = group[group["island_code"] == island]
                # get unique non-empty types
                unique_types = sorted(t for t in df_island["TP_CLS_ED_clean"].unique() if t)
                f.write(f"\t{EMOJI_ISLAND}  {island}:\t{EMOJI_BUILDING} {len(df_island)}\t{EMOJI_TYPE} {', '.join(unique_types) if unique_types else 'none'}\n")
            
            f.write("\n")  # blank line between sestiere sections

    print(f"✅ Summary complete. Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
