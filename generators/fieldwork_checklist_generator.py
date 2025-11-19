import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import ALIAS_CSV, FILTERED_ADDRESS_CSV, CHECKLISTS_DIR, TOTAL_CHECKLIST_CSV

import pandas as pd

def main():
    print(f"📁 Output directory: {CHECKLISTS_DIR}")

    # === Load data ===
    print("📂 Loading data...")
    df_buildings = pd.read_csv(ALIAS_CSV)
    df_addresses = pd.read_csv(FILTERED_ADDRESS_CSV)
    print(f"✅ Loaded {len(df_buildings)} buildings and {len(df_addresses)} addresses.\n")

    # === Determine islands and sestiere codes ===
    df_buildings["island_code"] = df_buildings["short_alias"].str[:4]
    df_buildings["sestiere_code"] = df_buildings["full_alias"].str[:2]
    islands_sestiere = df_buildings.groupby("island_code")["sestiere_code"].first().to_dict()
    print(f"🌊 Found {len(islands_sestiere)} islands: {', '.join(islands_sestiere.keys())}\n")

    all_islands_data = []

    # === Generate one checklist per island ===
    for island_code, sestiere_code in islands_sestiere.items():
        print(f"🏝️ Processing island {island_code} (Sestiere {sestiere_code})...")

        # Filter relevant rows
        df_buildings_island = df_buildings[df_buildings["short_alias"].str.startswith(island_code)]

        # Create Qu_Terra column if not already present
        if "Qu_Terra" not in df_buildings_island.columns:
            df_buildings_island["Qu_Terra"] = ""

        # Select and reorder columns
        grouped = df_buildings_island[["short_alias", "TP_CLS_ED", "Qu_Gronda", "Qu_Terra", "Superficie"]].copy()

        # === Add addresses with no building ===
        df_addresses_island = df_addresses[df_addresses["Codice_1"].fillna("").str.startswith(island_code[:3])]
        no_building = df_addresses_island[
            ~df_addresses_island["TARGET_FID_12_13"].isin(df_buildings_island.get("TARGET_FID_12_13", []))
        ]
        if not no_building.empty:
            no_building_grouped = pd.DataFrame([{
                "short_alias": f"{island_code}~NO_BUILDING",
                "TP_CLS_ED": "",
                "Qu_Gronda": "",
                "Qu_Terra": "",
                "Superficie": "",
            }])
            grouped = pd.concat([grouped.sort_values(by="short_alias"), no_building_grouped], ignore_index=True)

        # === Save per-island CSV ===
        output_csv = CHECKLISTS_DIR / f"{sestiere_code}-{island_code}.csv"
        grouped.to_csv(output_csv, index=False)
        print(f"💾 Saved checklist: {output_csv}")

        all_islands_data.append(grouped)

    # === Save total CSV for all islands ===
    if all_islands_data:
        total_df = pd.concat(all_islands_data, ignore_index=True).sort_values(by="short_alias")
        total_df.to_csv(TOTAL_CHECKLIST_CSV, index=False)
        print(f"\n💾 Saved total checklist: {TOTAL_CHECKLIST_CSV}")

    print("\n✅ All islands processed successfully!")

if __name__ == "__main__":
    main()