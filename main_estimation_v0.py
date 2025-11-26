import pandas as pd
from constants import ALIAS_GEOJSON, FILTERED_CSV, DATA_DIR, ESTIMATES_DIR
from dataset import Dataset
from plotter import plot_island_by_tract
from file_utils import load_csv

"""
Estimation Model V0 — Field Calculation Overview

floors_est:
    Estimated number of floors based on height difference:
        floors_est = round( (Qu_Gronda - Qu_Terra) / HEIGHT_PER_FLOOR )
    • Qu_Gronda = roof elevation
    • Qu_Terra = ground elevation
    • HEIGHT_PER_FLOOR = 3.2 meters per floor (assumed)
    • Minimum value is clamped to 1 floor

units_est_meters:
    Approximate unit count based on electrical meters associated with the building:
        units_est_meters = total number of linked meter records
    • Derived from address → meter relationships in the dataset
    • Assumes each meter corresponds to one unit

units_est_volume:
    Volume-based estimate using footprint area and floors:
        units_est_volume = round( (floors_est * Superficie) / SQUARE_FOOTAGE_PER_UNIT )
    • Superficie = building footprint area in m²
    • SQUARE_FOOTAGE_PER_UNIT = 50 m² per residential unit (assumed average)
    • Essentially: total habitable area / avg unit size

pop_est:
    Population estimated from tract-level census value (POP21):
        pop_est = round( POP21_for_tract / number_of_buildings_in_tract )
    • Even split across all buildings within the same SEZ21 tract
    • Buildings missing POP21 default to zero
"""

HEIGHT_PER_FLOOR = 3.2
SQUARE_FOOTAGE_PER_UNIT = 80.0

def estimation_v0():
    ds = Dataset(str(ALIAS_GEOJSON))
    bcsv = load_csv(FILTERED_CSV)

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

    out_df = pd.DataFrame(estimates)
    out_df = out_df.sort_values(by="short_alias", na_position="last")

    out_path = ESTIMATES_DIR / "VPC_Estimates_V0.csv"
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    plot_island_by_tract(ds, "MELO")

if __name__ == "__main__":
    estimation_v0()
    print(f"✅ Estimation complete. CSV saved to {DATA_DIR / 'VPC_Estimates_V0.csv'}")
