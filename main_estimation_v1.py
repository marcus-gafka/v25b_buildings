import pandas as pd
import numpy as np
from dataset import Dataset
from file_utils import load_csv
from constants import ESTIMATES_DIR, ALIAS_GEOJSON, FILTERED_CSV, LIN_REG_CSV, FILTERED_WATER_CSV
from math import ceil

AVERAGE_UNIT_AREA = 125  # m² per unit, adjust as needed
K_NEIGHBORS = 5          # number of neighbors to average


# ================================================================
# ---------------------- ΔQu CALCULATION --------------------------
# ================================================================
def compute_delta_qu(building, bcsv, all_buildings, k=K_NEIGHBORS):
    row = bcsv[bcsv["TARGET_FID_12_13"] == building.id]
    if row.empty:
        return 0
    qu_terra = row.iloc[0]["Qu_Terra"]
    qu_gronda = row.iloc[0]["Qu_Gronda"]

    if pd.notnull(qu_gronda) and qu_gronda not in [0, 9999]:
        return qu_gronda - qu_terra

    neighbors = []
    for b in all_buildings:
        if b == building:
            continue
        r = bcsv[bcsv["TARGET_FID_12_13"] == b.id]
        if r.empty:
            continue
        qg = r.iloc[0]["Qu_Gronda"]
        qt = r.iloc[0]["Qu_Terra"]
        if pd.notnull(qg) and qg not in [0, 9999] and pd.notnull(qt):
            neighbors.append((b, qg - qt))

    if not neighbors:
        raise RuntimeError(f"No valid neighbors found for building {building.id}")

    closest = sorted(neighbors, key=lambda x: building.centroid.distance(x[0].centroid))[:k]
    avg_delta = np.mean([d for _, d in closest])

    print(f"  [ΔQu] Building {building.id}: using avg ΔQu from {len(closest)} neighbors: {avg_delta}")
    return avg_delta


# ================================================================
# ------------------ SUPERFICIE / FOOTPRINT -----------------------
# ================================================================
def compute_valid_superficie(building, bcsv, all_buildings, k=K_NEIGHBORS):
    row = bcsv[bcsv["TARGET_FID_12_13"] == building.id]
    if row.empty:
        return 0
    superficie = row.iloc[0].get("Superficie", np.nan)

    if pd.notnull(superficie) and 0 < superficie < 30000:
        return superficie

    neighbors = []
    for b in all_buildings:
        if b == building:
            continue
        r = bcsv[bcsv["TARGET_FID_12_13"] == b.id]
        if r.empty:
            continue
        s = r.iloc[0].get("Superficie", np.nan)
        if pd.notnull(s) and 0 < s < 30000:
            neighbors.append((b, s))

    if not neighbors:
        raise RuntimeError(f"No valid footprint neighbors found for building {building.id}")

    closest = sorted(neighbors, key=lambda x: building.centroid.distance(x[0].centroid))[:k]
    avg_superficie = np.mean([s for _, s in closest])

    print(f"  [Superficie] Building {building.id}: using avg footprint from {len(closest)} neighbors: {avg_superficie}")
    return avg_superficie


# ================================================================
# -------------------- LOAD REGRESSION MODELS ---------------------
# ================================================================
def load_models():
    df = pd.read_csv(LIN_REG_CSV)
    df.fillna(0, inplace=True)
    models = {}
    for _, row in df.iterrows():
        models[row["TP_CLS_ED"]] = row["m_qu"], row["b_qu"], row["qu_count"]
    return models


# ================================================================
# ------------------------ UNIT COUNTS ----------------------------
# ================================================================
def estimate_units(building, meter_df):
    total_units = 0
    for addr in building.addresses:
        addr_meters = meter_df[meter_df["ProcessedAddress"] == addr.address]
        filtered_meters = addr_meters[addr_meters["Condominio"] != "X"]
        addr_units = filtered_meters[
            ["Nuclei_domestici", "Nuclei_commerciali", "Nuclei_non_residenti"]
        ].sum().sum()
        total_units += addr_units
        print(f"  [Units] Address {addr.address}: meters={len(addr_meters)}, filtered={len(filtered_meters)}, units={addr_units}")

    return int(total_units)


# ================================================================
# ------------ POPULATION PROPORTIONAL ALLOCATION ----------------
# ================================================================
def assign_population_estimates(est_df, bcsv):
    """
    Inputs:
        est_df: output estimates (floors, superficie, etc)
        bcsv: full building CSV (contains POP21 + SEZ21)
    Returns:
        est_df with pop_est assigned
    """

    merged = est_df.merge(
        bcsv[["TARGET_FID_12_13", "POP21", "SEZ21"]],
        left_on="building_id",
        right_on="TARGET_FID_12_13",
        how="left"
    )

    # usable = footprint * (floors - 1)
    merged["usable_area"] = merged["superficie"] * merged["floors_est"].clip(lower=1)
    merged["usable_area"] -= merged["superficie"]
    merged["usable_area"] = merged["usable_area"].clip(lower=0)

    # Sum per tract (SEZ21)
    tract_totals = merged.groupby("SEZ21")["usable_area"].sum().rename("tract_usable")
    merged = merged.join(tract_totals, on="SEZ21")

    # tract population (POP21 is constant per tract in your data)
    tract_pop = merged.groupby("SEZ21")["POP21"].max().rename("tract_population")
    merged = merged.join(tract_pop, on="SEZ21")

    merged["pop_est"] = np.where(
        merged["tract_usable"] > 0,
        merged["tract_population"] * (merged["usable_area"] / merged["tract_usable"]),
        0
    )

    return merged


# ================================================================
# --------------------- MAIN ESTIMATION LOOP ----------------------
# ================================================================
def estimation_v1():
    ds = Dataset(str(ALIAS_GEOJSON))
    bcsv = load_csv(FILTERED_CSV)
    meter_df = pd.read_csv(FILTERED_WATER_CSV)

    models = load_models()
    misc_model = models.get("misc", (0.229, 0.887, 0))

    building_map = {b.id: b for s in ds.venice.sestieri for i in s.islands for t in i.tracts for b in t.buildings}
    all_buildings = list(building_map.values())

    estimates = []

    for idx, (_, row) in enumerate(bcsv.iterrows(), start=1):
        b_id = row["TARGET_FID_12_13"]
        building = building_map.get(b_id)

        if building is None or building.short_alias is None or not building.short_alias.startswith("ZACC"):
            continue

        building_type = row.get("TP_CLS_ED", "misc")

        # ΔQu
        delta_qu = compute_delta_qu(building, bcsv, all_buildings)

        # Model select
        m, b, count = models.get(building_type, misc_model)
        if count < 10:
            m, b, count = misc_model

        floors_est = max(1, int(round(m * delta_qu + b)))

        # footprint
        superficie_valid = compute_valid_superficie(building, bcsv, all_buildings)

        # units
        units_est_meters = estimate_units(building, meter_df)
        units_est_volume = max(0, (floors_est - 1) * ceil(superficie_valid / AVERAGE_UNIT_AREA))

        estimates.append({
            "short_alias": building.short_alias,
            "building_id": building.id,
            "floors_est": floors_est,
            #"superficie": superficie_valid,
            #"units_est_meters": units_est_meters,
            #"units_est_volume": units_est_volume,
        })

        if idx % 200 == 0:
            print(f"Estimated {idx} buildings...")

    # -----------------------------------------------------------
    # Add population estimates
    # -----------------------------------------------------------
    est_df = pd.DataFrame(estimates)
    est_df = est_df.sort_values(by="short_alias", na_position="last")

    final_df = assign_population_estimates(est_df, bcsv)

    out_path = ESTIMATES_DIR / "VPC_Estimates_V1.csv"
    final_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"✅ Final estimation complete. CSV saved to {out_path}")


if __name__ == "__main__":
    estimation_v1()
