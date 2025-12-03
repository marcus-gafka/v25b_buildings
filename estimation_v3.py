import pandas as pd
import numpy as np
from constants import (
    ESTIMATES_DIR,
    FILTERED_CSV,
    FILTERED_WATER_CSV,
    LIN_REG_CSV,
    FILTERED_SURVEY_CSV,
    TOTAL_FIELDWORK_CSV,
    UNIT_INFO_CSV,
)

K_NEIGHBORS = 5
PRIMARY_WATER_CUTOFF = 5.0

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
def is_full_nr(tipofun, specfun, has_hotel):
    specfun_condition = specfun not in ("0", "00", "")
    tipofun_condition = tipofun.startswith("SP") if tipofun else False
    return specfun_condition or tipofun_condition or has_hotel

def attach_nr_info(ds):
    # Load CSVs (as before)
    unit_info_df = pd.read_csv(UNIT_INFO_CSV)
    survey_df = pd.read_csv(FILTERED_SURVEY_CSV)
    field_df = pd.read_csv(TOTAL_FIELDWORK_CSV)

    unit_info_df["short_alias"] = unit_info_df["short_alias"].str.upper()
    survey_df["short_alias"] = survey_df["short_alias"].str.upper()
    field_df["short_alias"] = field_df["short_alias"].str.upper()

    units_str_map = dict(zip(unit_info_df["short_alias"], unit_info_df.get("num_strs", [0]*len(unit_info_df))))
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
    for b in all_buildings:
        sha = (b.short_alias or "").strip().upper()
        b.units_str = int(units_str_map.get(sha, 0))
        b.units_empty = int(units_empty_map.get(sha, 0))
        b.measured = pd.notna(measured_map.get(sha, None))
        b.surveyed = sha in surveyed_set
        b.full_nr = is_full_nr(b.tipofun, b.specfun, b.has_hotel)

# ------------------------------------------------------------
# ESTIMATION V3
# ------------------------------------------------------------
def estimation_v3(ds, islands=None, debug=False):
    import os
    import pandas as pd

    # ---------------------- NR INFO ----------------------
    print("[STEP] Attaching NR info")

    all_buildings = []
    for s in ds.venice.sestieri:
        for i in s.islands:
            if islands and not any(i.code.startswith(isl) for isl in islands):
                continue
            for t in i.tracts:
                all_buildings.extend(t.buildings)

    print(f"[INFO] Total buildings to process: {len(all_buildings)}")

    # ---------------------- Load CSVs ----------------------
    print("[STEP] Loading CSVs and creating mappings")
    bcsv = pd.read_csv(FILTERED_CSV)
    meter_df = pd.read_csv(FILTERED_WATER_CSV)
    linreg_df = pd.read_csv(LIN_REG_CSV)
    linreg_map = {row["TP_CLS_ED"]: row for _, row in linreg_df.iterrows()}
    bcsv_by_id = bcsv.set_index("TARGET_FID_12_13")
    bcsv_by_tract = bcsv.set_index("SEZ21")

    # ---------------------- Assign building type ----------------------
    for idx, b in enumerate(all_buildings, 1):
        b.tp_cls = bcsv_by_id.loc[b.id].get("TP_CLS_ED", "unknown") if b.id in bcsv_by_id.index else "unknown"
        if idx % 100 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Assigned type to {idx}/{len(all_buildings)} buildings")

    # ---------------------- Compute normalized + floors + livable ----------------------
    print("[STEP] Computing normalized height, superficie, floors, meter units, livable space")
    for idx, b in enumerate(all_buildings, 1):
        set_normalized_height_and_superficie(b, all_buildings, debug=debug)

        # Floors estimation
        row = linreg_map.get(b.tp_cls)
        model = row if row is not None and row.get("qu_count", 0) >= 10 else linreg_df.iloc[-1]
        m_qu = model.get("m_qu")
        b_qu = model.get("b_qu")
        b.floors_est = max(1, int(round(m_qu * (b.normalized_height or 0) + b_qu)))

        b.units_est_meters = calc_units_from_meter_data(b, meter_df)
        b.livable_space = max(0, (b.floors_est - 1) * (b.normalized_superficie or 0))

        if idx % 50 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Processed {idx}/{len(all_buildings)} buildings for floors & units")

    # ---------------------- Tract-level allocation ----------------------
    print("[STEP] Assigning population & units per tract")
    tract_map = {}
    for b in all_buildings:
        if b.id in bcsv_by_id.index:
            tract_id = bcsv_by_id.loc[b.id].get("SEZ21")
            tract_map.setdefault(tract_id, []).append(b)

    for idx, (tract_id, buildings) in enumerate(tract_map.items(), 1):
        if tract_id in bcsv_by_tract.index:
            row = bcsv_by_tract.loc[tract_id]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            pop_total = int(row.get("POP21", 0))
            unit_total = int(row.get("ABI21", 0))
        else:
            pop_total = 0
            unit_total = 0

        total_livable = sum(b.livable_space or 0 for b in buildings)
        if total_livable == 0:
            for b in buildings:
                b.pop_est = 0
                b.units_est_volume = 0
                b.units_est_merged = 0
            if idx % 5 == 0 or idx == len(tract_map):
                print(f"[PROGRESS] Processed {idx}/{len(tract_map)} tracts")
            continue

        # Population allocation
        raw_pop = [(b, (b.livable_space / total_livable) * pop_total) for b in buildings]
        for b, v in raw_pop:
            b.pop_est = int(v)
        remainder_pop = pop_total - sum(b.pop_est for b, _ in raw_pop)
        frac_pop = sorted(raw_pop, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_pop):
            frac_pop[i % len(frac_pop)][0].pop_est += 1

        # Volume units allocation
        raw_units = [(b, (b.livable_space / total_livable) * unit_total) for b in buildings]
        for b, v in raw_units:
            b.units_est_volume = int(v)
        remainder_units = unit_total - sum(b.units_est_volume for b, _ in raw_units)
        frac_units = sorted(raw_units, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_units):
            frac_units[i % len(frac_units)][0].units_est_volume += 1

        # Merged units
        ALPHA = 0.6
        raw_merged = [(b, ALPHA * b.units_est_meters + (1 - ALPHA) * b.units_est_volume) for b in buildings]
        for b, v in raw_merged:
            b.units_est_merged = int(v)
        remainder_merged = unit_total - sum(b.units_est_merged for b, _ in raw_merged)
        frac_merged = sorted(raw_merged, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_merged):
            frac_merged[i % len(frac_merged)][0].units_est_merged += 1

        if idx % 5 == 0 or idx == len(tract_map):
            print(f"[PROGRESS] Processed {idx}/{len(tract_map)} tracts")

    # ---------------------- Units_calc, primary, secondary ----------------------
    print("[STEP] Calculating units_calc, primary, secondary for all buildings")
    meter_lists = {
        sha.upper(): [
            (row["Consumo_medio_2024"], row["Componenti"] if pd.notna(row["Componenti"]) and row["Componenti"] > 0 else 1)
            for _, row in df.iterrows()
        ]
        for sha, df in meter_df.groupby("ProcessedAddress")
    }

    for idx, b in enumerate(all_buildings, 1):
        merged = getattr(b, "units_est_merged", 0) or 0
        empty  = getattr(b, "units_empty", 0) or 0
        strs   = getattr(b, "units_str", 0) or 0
        b.units_calc = max(0, merged - empty - strs)

        primary_units = 0
        for addr in b.addresses:
            addr_key = addr.address.upper()
            consumptions = meter_lists.get(addr_key, [])
            for consumo, multiplier in consumptions:
                avg = float(consumo or 0) / multiplier
                if avg >= PRIMARY_WATER_CUTOFF:
                    primary_units += multiplier
                if debug:
                    print(f"[DEBUG] Addr {addr_key}: consumo={consumo}, comp={multiplier}, avg={avg}")

        b.units_primary = min(b.units_calc, primary_units)
        b.units_secondary = (b.units_calc - b.units_primary) + strs
        b.units_res = b.units_primary + b.units_secondary

        if idx % 100 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Calculated units for {idx}/{len(all_buildings)} buildings")

    # ---------------------- Build audit CSV ----------------------
    print("[STEP] Building audit rows and saving CSV")
    audit_rows = []
    for idx, b in enumerate(all_buildings, 1):
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
            "units_est_merged": b.units_est_merged,
            "pop_est": b.pop_est,
            "units_str": getattr(b, "units_str", 0),
            "units_empty": getattr(b, "units_empty", 0),
            "units_calc": getattr(b, "units_calc", 0),
            "units_primary": getattr(b, "units_primary", 0),
            "units_secondary": getattr(b, "units_secondary", 0),
            "units_res": getattr(b, "units_res", 0),
            "measured": getattr(b, "measured", False),
            "surveyed": getattr(b, "surveyed", False),
            "geometry": getattr(b, "geometry", None)
        })
        if idx % 100 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Added {idx}/{len(all_buildings)} buildings to audit rows")

    audit_df = pd.DataFrame(audit_rows).sort_values("short_alias")
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_V3.csv")
    audit_df.to_csv(output_path, index=False)
    print(f"✅ V3 estimation completed and saved to {output_path} ({len(audit_rows)} buildings)")

    return ds
