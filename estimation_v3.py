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
# ESTIMATION V3
# ------------------------------------------------------------
def estimation_v3(ds, islands=None, debug=False):
    import os
    import pandas as pd
    from math import ceil

    print(f"🏗️ Built hierarchy with {len(ds.venice.sestieri)} sestieri")

    # ---------------------- NR INFO ----------------------
    print("[STEP] Attaching NR info")
    attach_nr_info(ds)

    # Build flat list of buildings (with optional island filtering)
    all_buildings = []
    for s in ds.venice.sestieri:
        for i in s.islands:
            if islands and not any(i.code.startswith(isl) for isl in islands):
                continue
            for t in i.tracts:
                all_buildings.extend(t.buildings)

    # ---------------------- Load CSVs ----------------------
    print("[STEP] Loading CSVs and creating mappings")
    bcsv = pd.read_csv(FILTERED_CSV)
    meter_df = pd.read_csv(FILTERED_WATER_CSV)
    linreg_df = pd.read_csv(LIN_REG_CSV)

    linreg_map = {row["TP_CLS_ED"]: row for _, row in linreg_df.iterrows()}

    # Build lookup maps for speed
    bcsv_by_id = bcsv.set_index("TARGET_FID_12_13")
    bcsv_by_tract = bcsv.set_index("SEZ21")

    # ---------------------- Assign building type ----------------------
    for b in all_buildings:
        if b.id in bcsv_by_id.index:
            b.tp_cls = bcsv_by_id.loc[b.id].get("TP_CLS_ED", "unknown")
        else:
            b.tp_cls = "unknown"

    # ---------------------- Compute normalized + floors + raw livable ----------------------
    print("[STEP] Computing normalized height, superficie, floors, meter units, livable space")

    for b in all_buildings:
        if debug:
            print(f"[STEP] Processing building {b.short_alias} (ID {b.id})")

        set_normalized_height_and_superficie(b, all_buildings, debug=debug)

        # Choose LINREG model
        row = linreg_map.get(b.tp_cls)
        if row is not None and row.get("qu_count", 0) >= 10:
            model = row
        else:
            model = linreg_df.iloc[-1]  # fallback

        # Floors
        m_qu = model.get("m_qu", 0.236)
        b_qu = model.get("b_qu", 0.795)
        b.floors_est = max(1, int(round(m_qu * (b.normalized_height or 0) + b_qu)))

        # Meter-based units (kept)
        b.units_est_meters = calc_units_from_meter_data(b, meter_df)

        # Raw volume-based units — NOT used in final ABI21, but tracked
        b.units_est_volume = b.floors_est * ceil((b.normalized_superficie or 0) / AVERAGE_UNIT_AREA)

        # Livable space for population + unit shares
        b.livable_space = max(0, (b.floors_est - 1) * (b.normalized_superficie or 0))

        if debug:
            print(f"[DEBUG] {b.short_alias}: floors={b.floors_est}, "
                  f"raw_units={b.units_est_volume}, livable={b.livable_space}")

    # ---------------------- Tract-level allocation ----------------------
    print("[STEP] Assigning population & units per tract (POP21, ABI21)")

    # Map: tract_id -> list of buildings
    tract_map = {}
    for b in all_buildings:
        if b.id in bcsv_by_id.index:
            tract = bcsv_by_id.loc[b.id].get("SEZ21")
            tract_map.setdefault(tract, []).append(b)

    for tract_id, buildings in tract_map.items():
        if tract_id in bcsv_by_tract.index:
            row = bcsv_by_tract.loc[tract_id]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]

            pop_total = int(row.get("POP21", 0))
            unit_total = int(row.get("ABI21", 0))
        else:
            pop_total = 0
            unit_total = 0

        total_space = sum(b.livable_space or 0 for b in buildings)

        print(f"[DEBUG] Tract {tract_id}: livable={total_space}, POP21={pop_total}, ABI21={unit_total}")

        if total_space == 0:
            # All population is zero for the tract
            for b in buildings:
                b.pop_est = 0
            continue

        # ---------------- POPULATION: proportional integer allocation ----------------
        raw_pop = [(b, (b.livable_space / total_space) * pop_total) for b in buildings]

        # integer part
        for b, v in raw_pop:
            b.pop_est = int(v)

        # distribute remainder
        remainder = pop_total - sum(b.pop_est for b, v in raw_pop)
        frac = sorted(raw_pop, key=lambda x: x[1] - int(x[1]), reverse=True)
        for i in range(remainder):
            frac[i % len(frac)][0].pop_est += 1

        # ---------------- UNITS: ABI21-based allocation (ONLY source) ----------------
        raw_units = [(b, (b.livable_space / total_space) * unit_total) for b in buildings]

        for b, v in raw_units:
            b.units_est_volume = int(v)

        remainder_units = unit_total - sum(b.units_est_volume for b, v in raw_units)
        frac_u = sorted(raw_units, key=lambda x: x[1] - int(x[1]), reverse=True)
        for i in range(remainder_units):
            frac_u[i % len(frac_u)][0].units_est_volume += 1

        if debug:
            for b in buildings:
                print(f"[DEBUG] {b.short_alias}: final pop={b.pop_est}, units={b.units_est_volume}")

    # ---------------------- Build audit CSV ----------------------
    print("[STEP] Building audit rows")
    audit_rows = []
    for b in all_buildings:

        b.units_est_merged = (b.units_est_meters + b.units_est_volume)/2

        audit_rows.append({
            "short_alias": b.short_alias,
            "building_id": b.id,
            "type": b.tp_cls,
            "height": b.height,
            "norm_height": b.normalized_height,
            "superficie": b.superficie,
            "norm_superficie": b.normalized_superficie,
            "floors_est": b.floors_est,
            "units_est_meters": b.units_est_meters,
            "units_est_volume": b.units_est_volume,
            "units_est_merged:": b.units_est_merged,
            "pop_est": b.pop_est,
            "units_nr": getattr(b, "units_nr", 0),
            "units_empty": getattr(b, "units_empty", 0),
            "measured": getattr(b, "measured", False),
            "surveyed": getattr(b, "surveyed", False),
            "geometry": getattr(b, "geometry", None)
        })

    audit_df = pd.DataFrame(audit_rows).sort_values("short_alias")
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_V3.csv")
    audit_df.to_csv(output_path, index=False)

    print(f"✅ V3 estimation completed and saved to {output_path} ({len(audit_rows)} buildings)")

    return ds
