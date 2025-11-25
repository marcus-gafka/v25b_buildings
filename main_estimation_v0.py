# estimation_v0.py
from dataclasses import field
from typing import List
import pandas as pd
from constants import ALIAS_GEOJSON, FILTERED_CSV, FILTERED_STR_CSV, DATA_DIR
from dataset import Dataset
from plotter import plot_island_by_tract

# --- Estimation constants ---
HEIGHT_PER_FLOOR = 3.2  # meters per floor
SQUARE_FOOTAGE_PER_UNIT = 50.0  # m² per unit

def load_filtered_csv():
    df = pd.read_csv(FILTERED_CSV)
    df.columns = df.columns.str.strip()  # normalize columns
    required_cols = ["TARGET_FID_12_13", "Qu_Terra", "Qu_Gronda", "POP21", "Superficie", "SEZ21"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"❌ CSV must include '{col}' field.")
    return df

def load_strs():
    df = pd.read_csv(FILTERED_STR_CSV)
    df["ADDRESS"] = df["ADDRESS"].astype(str).str.strip().str.upper()
    return df

def estimation_v0():
    ds = Dataset(str(ALIAS_GEOJSON))
    bcsv = load_filtered_csv()
    str_df = load_strs()

    # Build address -> list of STR FIDs mapping
    strs_map = str_df.groupby("ADDRESS")["FID"].apply(list).to_dict()

    # Track number of buildings per tract for population splitting
    tract_building_counts = bcsv.groupby("SEZ21")["TARGET_FID_12_13"].count().to_dict()

    # Map building ID -> Building object
    building_map = {b.id: b for s in ds.venice.sestieri for i in s.islands for t in i.tracts for b in t.buildings}

    estimates = []

    for _, row in bcsv.iterrows():
        b_id = row["TARGET_FID_12_13"]
        building = building_map.get(b_id)
        if building is None:
            continue

        qu_terra = row["Qu_Terra"]
        qu_gronda = row["Qu_Gronda"]
        superficie = row["Superficie"]
        sez21 = row["SEZ21"]

        # --- Floors estimate ---
        if pd.notnull(qu_gronda) and pd.notnull(qu_terra):
            building.floors_est = max(1, int(round((qu_gronda - qu_terra) / HEIGHT_PER_FLOOR)))
        else:
            building.floors_est = 1

        # --- Units estimate from meters ---
        total_meters = sum(len(addr.meters) for addr in building.addresses)
        building.units_est_meters = total_meters

        # --- Units estimate from volume ---
        building.units_est_volume = int(round((building.floors_est * superficie) / SQUARE_FOOTAGE_PER_UNIT))

        # --- Population estimate ---
        n_buildings_in_tract = tract_building_counts.get(sez21, 1)
        tract_pop_value = row["POP21"]
        if pd.notnull(tract_pop_value):
            building.pop_est = int(round(tract_pop_value / n_buildings_in_tract))
        else:
            building.pop_est = 0

        estimates.append({
            "short_alias": building.short_alias,
            "building_id": building.id,
            "floors_est": building.floors_est,
            "units_est_meters": building.units_est_meters,
            "units_est_volume": building.units_est_volume,
            "pop_est": building.pop_est
        })

    # --- Save CSV ---
    out_df = pd.DataFrame(estimates)

    # --- Sort alphabetically by short_alias ---
    out_df = out_df.sort_values(by="short_alias", na_position="last")

    out_path = DATA_DIR / "VPC_Estimates_V0.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    plot_island_by_tract(ds, "MELO")

def main():
    estimation_v0()
    print(f"✅ Estimation complete. CSV saved to {DATA_DIR / 'VPC_Estimates_V0.csv'}")

if __name__ == "__main__":
    main()
