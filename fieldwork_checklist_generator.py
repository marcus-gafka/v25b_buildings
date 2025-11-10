import pandas as pd
from pathlib import Path
from constants import ALIAS_CSV, FILTERED_ADDRESS_CSV, CHECKLISTS_DIR
from estimation import estimate_floors

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

    # List to collect all island data
    all_islands_data = []

    # === Generate one checklist per island ===
    for island_code, sestiere_code in islands_sestiere.items():
        print(f"🏝️ Processing island {island_code} (Sestiere {sestiere_code})...")

        # Filter relevant rows
        df_buildings_island = df_buildings[df_buildings["short_alias"].str.startswith(island_code)]
        df_addresses_island = df_addresses[df_addresses["Codice_1"] == island_code]

        # Merge addresses
        df_merged = df_buildings_island.merge(
            df_addresses_island[["TARGET_FID_12_13", "Full_sesti"]],
            on="TARGET_FID_12_13",
            how="left"
        )

        # Aggregate addresses per building (include Superficie)
        grouped = (
            df_merged.groupby(
                ["TARGET_FID_12_13", "short_alias", "TP_CLS_ED", "Qu_Gronda", "Superficie"],
                dropna=False
            )
            .agg({
                "Full_sesti": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))) if x.notna().any() else "none"
            })
            .reset_index()
        )

        # === Apply floors estimation only ===
        grouped["floors_est"] = grouped.apply(lambda row: estimate_floors(row), axis=1)

        # === Clean and reorder columns ===
        grouped = grouped.rename(columns={"Full_sesti": "list_of_addresses"})
        grouped = grouped[
            ["short_alias", "TP_CLS_ED", "Qu_Gronda", "Superficie", "list_of_addresses", "floors_est"]
        ]

        # === Add addresses with no building ===
        no_building = df_addresses_island[
            ~df_addresses_island["TARGET_FID_12_13"].isin(df_buildings_island["TARGET_FID_12_13"])
        ]
        if not no_building.empty:
            no_building_grouped = pd.DataFrame([{
                "short_alias": f"{island_code}~NO_BUILDING",
                "TP_CLS_ED": "",
                "Qu_Gronda": "",
                "Superficie": "",
                "list_of_addresses": ", ".join(sorted(set(no_building["Full_sesti"].dropna().astype(str)))),
                "floors_est": ""
            }])
            grouped = pd.concat([grouped.sort_values(by="short_alias"), no_building_grouped], ignore_index=True)

        # === Save per-island CSV ===
        output_csv = CHECKLISTS_DIR / f"{sestiere_code}-{island_code}.csv"
        grouped.to_csv(output_csv, index=False)
        print(f"💾 Saved checklist: {output_csv}")

        # Add to total dataset
        all_islands_data.append(grouped)

    # === Save total CSV for all islands ===
    if all_islands_data:
        total_df = pd.concat(all_islands_data, ignore_index=True)
        total_df = total_df.sort_values(by="short_alias")
        total_output_csv = CHECKLISTS_DIR / "!TOTAL.csv"
        total_df.to_csv(total_output_csv, index=False)
        print(f"\n💾 Saved total checklist: {total_output_csv}")

    print("\n✅ All islands processed successfully!")

if __name__ == "__main__":
    main()
