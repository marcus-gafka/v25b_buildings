import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import ALIAS_CSV, SUMMARY_DIR

import pandas as pd

# Emoji definitions
EMOJI_SESTIERE = "🏘️"
EMOJI_ISLAND = "🏝️"
EMOJI_BUILDING = "🏠"
EMOJI_TYPE = "🏷️"

MASTER_OUTPUT_FILE = SUMMARY_DIR / "Venice_Summary.txt"

# Venice districts to include
SESTIERI = [
    "cannaregio",
    "castello",
    "dorsoduro",
    "san marco",
    "san polo",
    "santa croce",
    "giudecca",
]


def write_per_sestiere_file(df_s, sestiere_name):
    """Write individual summary file per sestiere."""
    filename = SUMMARY_DIR / f"{sestiere_name.replace(' ', '_').title()}_Summary.txt"
    islands = sorted(df_s["island_code"].dropna().unique())

    with open(filename, "w", encoding="utf-8") as f:

        # HEADER
        f.write(
            f"{EMOJI_SESTIERE}  Sestiere: {sestiere_name.title()}\t"
            f"{len(islands)} islands\t{len(df_s)} buildings\n\n"
        )

        # QUICK ISLAND SUMMARY
        for island in islands:
            df_island = df_s[df_s["island_code"] == island]
            unique_types = sorted(t for t in df_island["TP_CLS_ED_clean"].unique() if t)

            f.write(
                f"{EMOJI_ISLAND}  {island}:\t"
                f"{EMOJI_BUILDING} {len(df_island)}\t"
                f"{EMOJI_TYPE} {', '.join(unique_types) if unique_types else 'none'}\n"
            )

        # PER-ISLAND TYPE BREAKDOWN
        f.write("\n\n🏷️ Building type totals per island:\n\n")

        for island in islands:
            df_island = df_s[df_s["island_code"] == island]
            type_counts = df_island["TP_CLS_ED_clean"].value_counts()

            type_list = sorted([t for t in type_counts.index if t])
            max_len = max((len(t) for t in type_list), default=0)

            f.write(f"{EMOJI_ISLAND} {island} — {len(df_island)} buildings\n")

            for t in type_list:
                padded = t + ":" + " " * (max_len - len(t))
                f.write(f"   {EMOJI_TYPE} {padded}  {EMOJI_BUILDING} {type_counts[t]}\n")

            f.write("\n")

    print(f"  ✔️ {filename.name} written")


def write_master_summary(df):
    """Write the full original-style buildings_summary.txt covering all sestieri."""
    with open(MASTER_OUTPUT_FILE, "w", encoding="utf-8") as f:

        for sestiere in sorted(df["Nome_Sesti_clean"].unique()):
            df_s = df[df["Nome_Sesti_clean"] == sestiere]

            islands = sorted(df_s["island_code"].dropna().unique())
            total_buildings = len(df_s)

            # HEADER
            f.write(
                f"{EMOJI_SESTIERE}  Sestiere: {sestiere.title()}\t"
                f"{len(islands)} islands\t{total_buildings} buildings\n\n"
            )

            # ISLAND LIST
            for island in islands:
                df_island = df_s[df_s["island_code"] == island]
                unique_types = sorted(t for t in df_island["TP_CLS_ED_clean"].unique() if t)

                f.write(
                    f"\t{EMOJI_ISLAND}  {island}:\t"
                    f"{EMOJI_BUILDING} {len(df_island)}\t"
                    f"{EMOJI_TYPE} {', '.join(unique_types) if unique_types else 'none'}\n"
                )

            f.write("\n")

            # PER-SESTIERE TOTAL TYPE COUNTS
            f.write(f"🏷️ Total building types in {sestiere.title()}:\n")

            type_counts = df_s["TP_CLS_ED_clean"].value_counts()
            type_list = sorted([t for t in type_counts.index if t])
            max_len = max((len(t) for t in type_list), default=0)

            for t in type_list:
                padded_type = t + ":" + " " * (max_len - len(t))
                f.write(f"  {EMOJI_TYPE} {padded_type}  {EMOJI_BUILDING} {type_counts[t]}\n")

            f.write("\n\n")

        # --- GLOBAL TOTALS ACROSS ALL SESTIERI ---
        f.write("=============================================\n")
        f.write("🏛️ TOTAL BUILDING TYPES ACROSS ALL SESTIERI\n")
        f.write("=============================================\n\n")

        global_counts = (
            df["TP_CLS_ED_clean"]
            .value_counts()
            .drop(labels=[""], errors="ignore")  # remove empty types
            .sort_values(ascending=False)
        )

        max_len_global = max((len(t) for t in global_counts.index), default=0)

        for t, count in global_counts.items():
            padded = t + ":" + " " * (max_len_global - len(t))
            f.write(f"  {EMOJI_TYPE} {padded}  {EMOJI_BUILDING} {count}\n")

        f.write("\n\n")

    print(f"  ✔️ Master summary written → {MASTER_OUTPUT_FILE}")

def main():
    print("📂 Loading building data...")
    df = pd.read_csv(ALIAS_CSV)
    print(f"✅ Loaded {len(df)} rows total\n")

    # Check required cols
    required_cols = {"Nome_Sesti", "short_alias", "TP_CLS_ED"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Clean + add fields
    df["Nome_Sesti_clean"] = df["Nome_Sesti"].fillna("").str.strip().str.lower()
    df["island_code"] = df["short_alias"].str[:4]
    df["TP_CLS_ED_clean"] = df["TP_CLS_ED"].fillna("").str.strip()

    SUMMARY_DIR.mkdir(exist_ok=True)
    print("🔎 Creating all sestiere summaries…\n")

    for s in SESTIERI:
        df_s = df[df["Nome_Sesti_clean"] == s]
        write_per_sestiere_file(df_s, s)

    print("\n🧩 Creating master combined summary…")
    write_master_summary(df)

    print("\n🎉 All summaries complete!")


if __name__ == "__main__":
    main()
