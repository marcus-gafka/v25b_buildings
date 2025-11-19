import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import ALIAS_CSV, FILTERED_ADDRESS_CSV, CHECKLISTS_DIR, TOTAL_ADDRESS_CSV

import pandas as pd
import re

def sort_key(addr):
    """
    Split an address like SP2149A into:
      ('SP', 2149, 'A') for sorting
    """
    if pd.isna(addr) or addr == "":
        return ("", 0, "")
    match = re.match(r"([A-Z]+)(\d+)([A-Z]*)", addr.upper())
    if match:
        letters, number, suffix = match.groups()
        return (letters, int(number), suffix)
    else:
        return (addr, 0, "")

def get_sestiere_code(val):
    """Return first 2 letters of sestiere if letters, else XX"""
    if isinstance(val, str) and len(val) >= 2 and val[:2].isalpha():
        return val[:2].upper()
    return "XX"

def main():
    print(f"📁 Output directory: {CHECKLISTS_DIR}")

    # === Load CSVs ===
    print("📂 Loading data...")
    df_alias = pd.read_csv(ALIAS_CSV, usecols=["short_alias", "TARGET_FID_12_13"])
    df_addr = pd.read_csv(FILTERED_ADDRESS_CSV)
    print(f"✅ Loaded {len(df_alias)} building aliases and {len(df_addr)} addresses.\n")

    # === Merge on TARGET_FID_12_13 ===
    merged = df_addr.merge(df_alias, on="TARGET_FID_12_13", how="left")

    # === Extract codes ===
    merged["island_code"] = merged["Codice_1"]
    merged["sestiere_code"] = merged["Full_sesti"].apply(get_sestiere_code)

    # === Drop rows with no island code (optional) ===
    merged = merged.dropna(subset=["island_code"])

    # === Group and save per island ===
    all_islands = []
    for island_code, group in merged.groupby("island_code"):
        sestiere_code = group["sestiere_code"].dropna().iloc[0]
        output_csv = CHECKLISTS_DIR / f"{sestiere_code}-{island_code}-A.csv"

        # === Sort by Full_sesti ===
        group = group.sort_values("Full_sesti", key=lambda x: x.map(sort_key))

        # Save only Full_sesti and short_alias
        group[["Full_sesti", "short_alias"]].to_csv(output_csv, index=False)
        all_islands.append(group)
        print(f"💾 Saved island CSV: {output_csv}")

    # === Save combined total ===
    if all_islands:
        total_df = pd.concat(all_islands, ignore_index=True)
        total_df = total_df.sort_values("Full_sesti", key=lambda x: x.map(sort_key))
        total_df[["Full_sesti", "short_alias"]].to_csv(TOTAL_ADDRESS_CSV, index=False)
        print(f"\n💾 Saved total address CSV: {TOTAL_ADDRESS_CSV}")

    print("\n✅ All islands processed successfully!")

if __name__ == "__main__":
    main()
