import pandas as pd
from pathlib import Path
from constants import ALIAS_CSV, FILTERED_ADDRESS_CSV, CHECKLISTS_DIR

def main():
    print(f"📁 Output directory: {CHECKLISTS_DIR}")

    # === Load data ===
    print("📂 Loading data...")
    df_buildings = pd.read_csv(ALIAS_CSV)
    df_addresses = pd.read_csv(FILTERED_ADDRESS_CSV)
    print(f"✅ Loaded {len(df_buildings)} buildings and {len(df_addresses)} addresses.\n")

    # === Find all unique islands with sestiere codes ===
    df_buildings["island_code"] = df_buildings["short_alias"].str[:4]
    df_buildings["sestiere_code"] = df_buildings["full_alias"].str[:2]
    islands_sestiere = df_buildings.groupby("island_code")["sestiere_code"].first().to_dict()
    print(f"🌊 Found {len(islands_sestiere)} islands: {', '.join(islands_sestiere.keys())}\n")

    # === Generate one checklist per island ===
    for island_code, sestiere_code in islands_sestiere.items():
        print(f"🏝️ Processing island {island_code} (Sestiere {sestiere_code})...")

        # Filter data
        df_buildings_island = df_buildings[df_buildings["short_alias"].str.startswith(island_code)]
        df_addresses_island = df_addresses[df_addresses["Codice_1"] == island_code]

        # Merge and aggregate
        df_merged = df_buildings_island.merge(
            df_addresses_island[["TARGET_FID_12_13", "Full_sesti"]],
            on="TARGET_FID_12_13",
            how="left"
        )

        grouped = df_merged.groupby(["TARGET_FID_12_13", "short_alias"], dropna=False).agg({
            "Full_sesti": lambda x: ", ".join(sorted(set(x.dropna().astype(str)))) if x.notna().any() else "none"
        }).reset_index()

        # Clean + reorder
        grouped = grouped.rename(columns={"Full_sesti": "list_of_addresses"})
        grouped = grouped[["short_alias", "list_of_addresses"]].sort_values(by="short_alias")

        # Save with Sestiere-Island prefix
        output_csv = CHECKLISTS_DIR / f"{sestiere_code}-{island_code}.csv"
        grouped.to_csv(output_csv, index=False)
        print(f"💾 Saved checklist: {output_csv}")

    print("\n✅ All islands processed successfully!")

if __name__ == "__main__":
    main()
