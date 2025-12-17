import pandas as pd
import numpy as np
from math import ceil
import os
from file_utils import load_csv
from constants import (
    ESTIMATES_DIR,
    FILTERED_CSV,
    FILTERED_WATER_CSV,
)

HEIGHT_PER_FLOOR = 3.2
AVERAGE_UNIT_AREA = 125.0
K_NEIGHBORS = 5

# ------------------------------------------------------------
# UNITS FROM WATER METERS
# ------------------------------------------------------------
def calc_units_from_meter_data(building, meter_df):
    total_units = 0
    for addr in building.addresses:
        addr_meters = meter_df[meter_df["ProcessedAddress"] == addr.address]
        filtered = addr_meters[addr_meters["Condominio"] != "X"]

        for _, row in filtered.iterrows():
            multiplier = row["Componenti"] if pd.notna(row["Componenti"]) and row["Componenti"] != "" else 1
            subtotal = row[["Nuclei_domestici", "Nuclei_commerciali", "Nuclei_non_residenti"]].sum()
            total_units += subtotal * multiplier

    return int(total_units)

# ------------------------------------------------------------
# NORMALIZATION HELPER
# ------------------------------------------------------------
def set_normalized_height_and_superficie(building, all_buildings, k=K_NEIGHBORS, debug=False):
    # ------------------------
    # Height & Normalized Height
    # ------------------------
    if building.qu_terra is None:
        building.qu_terra = 0

    if building.qu_gronda not in [None, 0, 9999]:
        building.height = building.qu_gronda - building.qu_terra
        building.normalized_height = building.height
        if debug:
            print(f"Building {building.id} valid qu_gronda: height={building.height:.2f}")
    else:
        neighbors = [
            b for b in all_buildings
            if b != building
            and getattr(b, "island", None) == getattr(building, "island", None)
            and b.qu_gronda not in [None, 0, 9999]
        ]
        if neighbors:
            neighbors = sorted(neighbors, key=lambda b2: building.centroid.distance(b2.centroid))[:k]
            avg_qu_gronda = np.mean([b2.qu_gronda for b2 in neighbors])
            building.height = 0
            building.normalized_height = round(avg_qu_gronda - building.qu_terra,2)
        else:
            building.height = 0
            building.normalized_height = 0

    # ------------------------
    # Normalized Superficie
    # ------------------------
    if building.superficie is not None and 0 < building.superficie < 30000:
        building.normalized_superficie = building.superficie
    else:
        neighbors_s = [b for b in all_buildings if b != building and b.superficie is not None and 0 < b.superficie < 30000]
        if neighbors_s:
            neighbors_s = sorted(neighbors_s, key=lambda b2: building.centroid.distance(b2.centroid))[:k]
            building.normalized_superficie = round(np.mean([b2.superficie for b2 in neighbors_s]),2)
        else:
            building.normalized_superficie = 0

# ------------------------------------------------------------
# V1 ESTIMATION
# ------------------------------------------------------------
def estimation_v1(ds, islands=None, debug=False):
    """
    Populate building objects with V1 estimates, using normalized height and superficie,
    and export a CSV with key metrics for each building.
    """

    bcsv = load_csv(FILTERED_CSV)
    building_map = {b.id: b for s in ds.venice.sestieri for i in s.islands for t in i.tracts for b in t.buildings}
    all_buildings = list(building_map.values())
    meter_df = pd.read_csv(FILTERED_WATER_CSV)

    results = []

    for building in all_buildings:

        # optional island filter
        if islands and not any(building.short_alias.startswith(isl) for isl in islands):
            continue

        # normalize height & superficie
        set_normalized_height_and_superficie(building, all_buildings, k=K_NEIGHBORS, debug=debug)

        # units
        building.units_est_meters = calc_units_from_meter_data(building, meter_df)
        building.units_est_volume = max(
            0, (ceil(building.normalized_height / HEIGHT_PER_FLOOR)) * ceil(building.normalized_superficie / AVERAGE_UNIT_AREA)
        )

        # floors estimate
        building.floors_est = max(1, ceil(building.normalized_height / HEIGHT_PER_FLOOR))

        # population estimate
        row = bcsv.loc[bcsv["TARGET_FID_12_13"] == building.id]
        if not row.empty:
            tract_buildings = bcsv[bcsv["SEZ21"] == row.iloc[0]["SEZ21"]]
            n_blds = len(tract_buildings)
            pop_val = row.iloc[0].get("POP21", 0)
            building.pop_est = int(round(pop_val / n_blds)) if n_blds > 0 else 0
        else:
            building.pop_est = 0

        # append to CSV results
        results.append({
            "short_alias": building.short_alias,
            "building_id": building.id,
            "height": building.height,
            "norm_height": building.normalized_height,
            "superficie": building.superficie,
            "norm_superficie": building.normalized_superficie,
            "floors_est": building.floors_est,
            "units_est_meters": building.units_est_meters,
            "units_est_volume": building.units_est_volume,
            "pop_est": building.pop_est
        })

    # save CSV
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_v1.csv")
    pd.DataFrame(results).to_csv(output_path, index=False)
    print(f"✅ V1 estimation populated and saved to {output_path} for {len(results)} buildings")

    return ds
