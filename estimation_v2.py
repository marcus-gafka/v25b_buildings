import pandas as pd
import numpy as np
from math import ceil
import os
from file_utils import load_csv
from constants import (
    ESTIMATES_DIR,
    FILTERED_CSV,
    FILTERED_WATER_CSV,
    LIN_REG_CSV,
    FILTERED_SURVEY_CSV,
    FILTERED_ADDRESS_CSV,
    TOTAL_FIELDWORK_CSV,
    UNIT_INFO_CSV,
)

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
    if building.qu_terra is None:
        building.qu_terra = 0

    if building.qu_gronda not in [None, 0, 9999]:
        building.height = building.qu_gronda - building.qu_terra
        building.normalized_height = building.height
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
            building.normalized_height = round(avg_qu_gronda - building.qu_terra, 2)
        else:
            building.height = 0
            building.normalized_height = 0

    if building.superficie is not None and 0 < building.superficie < 30000:
        building.normalized_superficie = building.superficie
    else:
        neighbors_s = [b for b in all_buildings if b != building and b.superficie is not None and 0 < b.superficie < 30000]
        if neighbors_s:
            neighbors_s = sorted(neighbors_s, key=lambda b2: building.centroid.distance(b2.centroid))[:k]
            building.normalized_superficie = round(np.mean([b2.superficie for b2 in neighbors_s]), 2)
        else:
            building.normalized_superficie = 0

# ------------------------------------------------------------
# ATTACH NR INFO
# ------------------------------------------------------------
def attach_nr_info(ds):
    # Load CSVs (as before)
    unit_info_df = pd.read_csv(UNIT_INFO_CSV)
    survey_df = pd.read_csv(FILTERED_SURVEY_CSV)
    field_df = pd.read_csv(TOTAL_FIELDWORK_CSV)

    unit_info_df["short_alias"] = unit_info_df["short_alias"].str.upper()
    survey_df["short_alias"] = survey_df["short_alias"].str.upper()
    field_df["short_alias"] = field_df["short_alias"].str.upper()

    units_nr_map = dict(zip(unit_info_df["short_alias"], unit_info_df.get("num_strs", [0]*len(unit_info_df))))
    units_empty_map = dict(zip(unit_info_df["short_alias"], unit_info_df.get("num_zero_consumption_meters", [0]*len(unit_info_df))))
    measured_map = dict(zip(field_df["short_alias"], field_df.get("Measured Height", [np.nan]*len(field_df))))
    surveyed_set = set(survey_df["short_alias"])

    # Flatten buildings from all sestieri → islands → tracts
    all_buildings = [
        b
        for s in ds.venice.sestieri
        for isl in s.islands
        for t in isl.tracts
        for b in t.buildings
    ]

    # Update building objects
    for building in all_buildings:
        sha = (building.short_alias or "").strip().upper()
        building.units_nr = int(units_nr_map.get(sha, 0))
        building.units_empty = int(units_empty_map.get(sha, 0))
        building.measured = pd.notna(measured_map.get(sha, None))
        building.surveyed = sha in surveyed_set

# ------------------------------------------------------------
# ESTIMATION V2
# ------------------------------------------------------------
def estimation_v2(ds, islands=None, debug=False):
    import os
    import pandas as pd
    from math import ceil

    print(f"🏗️ Built hierarchy with {len(ds.venice.sestieri)} sestieri")

    # ---------------------- NR INFO ----------------------
    print("[STEP] Attaching NR info")
    attach_nr_info(ds)
    all_buildings = [b for s in ds.venice.sestieri for i in s.islands for t in i.tracts for b in t.buildings]

    # ---------------------- Preload CSVs ----------------------
    print("[STEP] Loading CSVs and creating mappings")
    bcsv = pd.read_csv(FILTERED_CSV)
    meter_df = pd.read_csv(FILTERED_WATER_CSV)
    linreg_df = pd.read_csv(LIN_REG_CSV)
    linreg_map = {row["TP_CLS_ED"]: row for _, row in linreg_df.iterrows()}

    # ---------------------- Assign original building type for all buildings ----------------------
    for building in all_buildings:
        row = bcsv.loc[bcsv["TARGET_FID_12_13"] == building.id]
        if not row.empty:
            building.tp_cls = row.iloc[0].get("TP_CLS_ED", "unknown")
        else:
            building.tp_cls = "unknown"

    # ---------------------- Compute normalized fields, floors, units ----------------------
    print("[STEP] Computing normalized height, superficie, floors, units, livable space")
    for count, building in enumerate(all_buildings, 1):
        if islands and not any(building.short_alias.startswith(isl) for isl in islands):
            continue

        print(f"[STEP] Processing building {building.short_alias} (ID {building.id})")
        set_normalized_height_and_superficie(building, all_buildings, debug=debug)
        print(f"[DEBUG] Normalized height: {building.normalized_height}, superficie: {building.normalized_superficie}")

        # LIN_REG fallback
        row = bcsv.loc[bcsv["TARGET_FID_12_13"] == building.id]
        tp_cls = building.tp_cls
        lin_row = linreg_map.get(tp_cls)

        if lin_row is not None and lin_row.get("qu_count", 0) >= 10:
            tp_row = lin_row
        else:
            tp_row = linreg_df.iloc[-1]  # fallback model for floors

        # Floors estimate using LIN_REG
        m_qu = tp_row.get("m_qu", 0.236)
        b_qu = tp_row.get("b_qu", 0.795)
        building.floors_est = max(1, int(round(m_qu * (building.normalized_height or 0) + b_qu)))

        print(f"[DEBUG] Building {building.short_alias} ({building.id}): "
              f"Original type={tp_cls}, LIN_REG model used={tp_row['TP_CLS_ED']}, floors_est={building.floors_est}")

        # Units & livable space
        building.units_est_meters = calc_units_from_meter_data(building, meter_df)
        building.units_est_volume = building.floors_est * ceil((building.normalized_superficie or 0) / 125.0)
        building.livable_space = max(0, (building.floors_est - 1) * (building.normalized_superficie or 0))
        print(f"[DEBUG] Units: meters={building.units_est_meters}, volume={building.units_est_volume}, "
              f"livable_space={building.livable_space}")

    # ---------------------- Population allocation ----------------------
    print("[STEP] Assigning population per tract")
    # Build tract -> building object mapping
    tract_map = {}
    for building in all_buildings:
        row = bcsv.loc[bcsv["TARGET_FID_12_13"] == building.id]
        if not row.empty:
            tract_id = row.iloc[0]["SEZ21"]
            tract_map.setdefault(tract_id, []).append(building)

    for tract_id, tract_buildings_objs in tract_map.items():
        pop_val = 0
        if tract_buildings_objs:
            row = bcsv.loc[bcsv["SEZ21"] == tract_id]
            if not row.empty:
                pop_val = row.iloc[0].get("POP21", 0)

        tract_space = sum(b.livable_space or 0 for b in tract_buildings_objs)
        if tract_space == 0:
            for b in tract_buildings_objs:
                b.pop_est = 0
            continue

        print(f"[DEBUG] Tract {tract_id} total livable_space: {tract_space}, POP21={pop_val}")
        raw_pops = [(b, (b.livable_space or 0) / tract_space * pop_val) for b in tract_buildings_objs]

        # Assign integer part
        for b, val in raw_pops:
            b.pop_est = int(val)

        # Distribute remainder using largest fractional parts
        remaining = int(round(pop_val - sum(b.pop_est for b, val in raw_pops)))
        frac_order = sorted(raw_pops, key=lambda x: x[1] - int(x[1]), reverse=True)
        for i in range(remaining):
            frac_order[i % len(frac_order)][0].pop_est += 1

        for b in tract_buildings_objs:
            print(f"[DEBUG] Building {b.short_alias} final pop_est: {b.pop_est}")

    # ---------------------- Build audit CSV ----------------------
    print("[STEP] Building audit rows")
    audit_rows = []
    for building in all_buildings:
        audit_rows.append({
            "short_alias": building.short_alias,
            "building_id": building.id,
            "type": building.tp_cls,
            "height": building.height,
            "norm_height": building.normalized_height,
            "superficie": building.superficie,
            "norm_superficie": building.normalized_superficie,
            "floors_est": building.floors_est,
            "units_est_meters": building.units_est_meters,
            "units_est_volume": building.units_est_volume,
            "pop_est": building.pop_est,
            "units_nr": getattr(building, "units_nr", 0),
            "units_empty": getattr(building, "units_empty", 0),
            "measured": getattr(building, "measured", False),
            "surveyed": getattr(building, "surveyed", False),
            "geometry": getattr(building, "geometry", None)
        })

        #print(getattr(building, "geometry"))

    audit_df = pd.DataFrame(audit_rows).sort_values("short_alias")
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_V2.csv")
    audit_df.to_csv(output_path, index=False)
    print(f"✅ V2 estimation completed and saved to {output_path} ({len(audit_rows)} buildings)")

    return ds
