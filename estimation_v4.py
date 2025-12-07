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
    UNINHABITED_CSV
)

K_NEIGHBORS = 5
EMPTY_UNIT_CUTOFF = 0.5

# ------------------------------------------------------------
# UNITS FROM WATER METERS
# ------------------------------------------------------------
def calc_units_from_meter_data(building, meter_df):
    total_units = 0

    for addr in building.addresses:
        addr_meters = meter_df[meter_df["ProcessedAddress"] == addr.address]

        filtered = addr_meters[addr_meters["Condominio"] != "X"]
        filtered = filtered[filtered["Cat_Tariffa"].str.strip().str.lower() != "uso pubblico"]

        for _, row in filtered.iterrows():
            multiplier = (
                row["Componenti"]
                if pd.notna(row["Componenti"]) and row["Componenti"] != ""
                else 1
            )

            subtotal = row[
                ["Nuclei_domestici", "Nuclei_commerciali", "Nuclei_non_residenti"]
            ].sum()

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
def is_full_nr(tipofun, specfun, dest, tp_cls, has_hotel, pop21, abi21, edi21):
    reasons = []

    if specfun not in ("0", "00", ""):
        reasons.append(f"specfun={specfun} not in ('0','00','')")
    if tipofun and tipofun not in ("0", "SP15", "SP16", "SP17"):
        reasons.append(f"tipofun={tipofun} triggers full NR (not 0/SP15/SP16/SP17)")
    if tp_cls and tp_cls in ("SU", "SM"):
        reasons.append(f"tp_cls={tp_cls} triggers full NR (not SU/SM)")
    if has_hotel:
        reasons.append("has_hotel=True")
    if dest not in ("H", "xx"):
        reasons.append(f"dest={dest} not in ('H','xx')")
    if any(x == 0 for x in (pop21, abi21, edi21)):
        pop_str = f"pop21={pop21}, abi21={abi21}, edi21={edi21}"
        reasons.append(f"one of population fields is 0 ({pop_str})")

    return len(reasons) > 0, reasons

def attach_nr_info(ds):
    # Load CSVs (as before)
    unit_info_df = pd.read_csv(UNIT_INFO_CSV)
    survey_df = pd.read_csv(FILTERED_SURVEY_CSV)
    field_df = pd.read_csv(TOTAL_FIELDWORK_CSV)

    # NEW: load uninhabited buildings CSV
    uninhabited_df = pd.read_csv(UNINHABITED_CSV)
    uninhabited_aliases = set(
        uninhabited_df["full_alias"].astype(str).str.upper().str.strip()
    )

    # Normalize short_alias fields
    unit_info_df["short_alias"] = unit_info_df["short_alias"].str.upper()
    survey_df["short_alias"] = survey_df["short_alias"].str.upper()
    field_df["short_alias"] = field_df["short_alias"].str.upper()

    # Maps and lookups
    units_str_map = dict(zip(
        unit_info_df["short_alias"],
        unit_info_df.get("num_strs", [0] * len(unit_info_df))
    ))

    units_empty_map = dict(zip(
        unit_info_df["short_alias"],
        unit_info_df.get("num_zero_consumption_meters", [0] * len(unit_info_df))
    ))

    measured_map = dict(zip(
        field_df["short_alias"],
        field_df.get("Measured Height", [np.nan] * len(field_df))
    ))

    surveyed_set = set(survey_df["short_alias"])

    # Flatten Venice → sestieri → islands → tracts
    all_tracts = [
        t
        for s in ds.venice.sestieri
        for isl in s.islands
        for t in isl.tracts
    ]

    # Update building objects
    for t in all_tracts:
        for b in t.buildings:
            sha = (b.short_alias or "").strip().upper()
            fa = (b.full_alias or "").strip().upper()

            # Existing NR details
            b.units_str = int(units_str_map.get(sha, 0))
            b.units_empty = int(units_empty_map.get(sha, 0))
            b.measured = pd.notna(measured_map.get(sha, None))
            b.surveyed = sha in surveyed_set

            # NEW: NR if in uninhabited list OR matches old logic
            nr_flag, nr_reasons = is_full_nr(
                b.tipo_fun, b.spec_fun, b.dest_pt_an, b.tp_cls, b.has_hotel,
                t.pop21, t.abi21, t.edi21
            )

            csv_flag = fa in uninhabited_aliases
            if csv_flag:
                nr_reasons.append("listed in Uninhabited CSV")

            b.full_nr = nr_flag or csv_flag

            # Debug print
            if b.full_nr and (b.short_alias or "").upper().startswith("MELO"):
                print(f"[NR] {b.full_alias} → {', '.join(nr_reasons)}")

def val_zero(x, is_number=True):
        if x is None:
            return 0 if is_number else ""
        return x

# ------------------------------------------------------------
# ESTIMATION V4
# ------------------------------------------------------------
def estimation_v4(ds, islands=None, debug=False):
    import os
    import pandas as pd
    from rtree import index

    # ---------------------- NR INFO ----------------------
    print("[STEP] Attaching NR info")
    attach_nr_info(ds)

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

        # --- Read tract totals ---
        if tract_id in bcsv_by_tract.index:
            row = bcsv_by_tract.loc[tract_id]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            pop_total = int(row.get("POP21", 0))
            unit_total = int(row.get("ABI21", 0))
        else:
            pop_total = 0
            unit_total = 0

        # --- Split NR vs RES buildings ---
        nr_buildings = [b for b in buildings if getattr(b, "full_nr", False)]
        res_buildings = [b for b in buildings if not getattr(b, "full_nr", False)]

        # NR buildings ALWAYS receive zero residential alloc.
        for b in nr_buildings:
            b.pop_est = 0
            b.units_est_volume = 0
            b.units_est_meters = 0
            b.units_est_merged = 0

        if not res_buildings:
            continue

        # --- Livable space only from RES buildings ---
        total_livable = sum(b.livable_space or 0 for b in res_buildings)
        if total_livable == 0:
            for b in res_buildings:
                b.pop_est = 0
                b.units_est_volume = 0
                b.units_est_merged = 0
            continue

        # -------- POPULATION ALLOCATION (RES only) --------
        raw_pop = [(b, (b.livable_space / total_livable) * pop_total) for b in res_buildings]
        for b, v in raw_pop:
            b.pop_est = int(v)
        remainder_pop = pop_total - sum(b.pop_est for b, _ in raw_pop)
        frac_pop = sorted(raw_pop, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_pop):
            frac_pop[i % len(frac_pop)][0].pop_est += 1

        # -------- VOLUME UNITS ALLOCATION (RES only) --------
        raw_units = [(b, (b.livable_space / total_livable) * unit_total) for b in res_buildings]
        for b, v in raw_units:
            b.units_est_volume = int(v)
        remainder_units = unit_total - sum(b.units_est_volume for b, _ in raw_units)
        frac_units = sorted(raw_units, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_units):
            frac_units[i % len(frac_units)][0].units_est_volume += 1

        # -------- MERGED UNITS ALLOCATION (RES only) --------
        ALPHA = 0.6
        raw_merged = [(b, ALPHA * b.units_est_meters + (1 - ALPHA) * b.units_est_volume)
                    for b in res_buildings]
        for b, v in raw_merged:
            b.units_est_merged = int(v)
        remainder_merged = unit_total - sum(b.units_est_merged for b, _ in raw_merged)
        frac_merged = sorted(raw_merged, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_merged):
            frac_merged[i % len(frac_merged)][0].units_est_merged += 1

    # ---------------------- Build meter lists ----------------------
    EMPTY_UNIT_CUTOFF = 0.5
    meter_lists = {
        sha.upper(): [
            (
                row["Consumo_medio_2024"],
                row["Componenti"] if pd.notna(row["Componenti"]) and row["Componenti"] > 0 else 1,
                row["Cat_Tariffa"] if pd.notna(row["Cat_Tariffa"]) else ""
            )
            for _, row in df.iterrows()
        ]
        for sha, df in meter_df.groupby("ProcessedAddress")
    }

    # ---------------------- Spatial index ----------------------
    idx_rtree = index.Index()
    building_map = {}

    for i, b in enumerate(all_buildings):
        merged = getattr(b, "units_est_merged", 0) or 0
        b._merged = merged

        # Count raw meters
        m_res = m_res_empty = m_nr = m_nr_empty = 0
        for addr in b.addresses:
            addr_key = addr.address.upper()
            for consumo, componenti, rate in meter_lists.get(addr_key, []):
                comp = componenti or 1
                rate_l = (rate or "").lower()
                is_res = "uso domestico residente" in rate_l
                is_empty = consumo is not None and consumo < EMPTY_UNIT_CUTOFF

                if is_res:
                    if is_empty:
                        m_res_empty += comp
                    else:
                        m_res += comp
                else:
                    if is_empty:
                        m_nr_empty += comp
                    else:
                        m_nr += comp

        b._m_res = m_res
        b._m_res_empty = m_res_empty
        b._m_nr = m_nr
        b._m_nr_empty = m_nr_empty
        b._meter_total = m_res + m_res_empty + m_nr + m_nr_empty

        if b._meter_total > 0:
            x, y = b.geometry.centroid.x, b.geometry.centroid.y
            idx_rtree.insert(i, (x, y, x, y))
            building_map[i] = b

    # ---------------------- Assign proportional units ----------------------
    for idx, b in enumerate(all_buildings, 1):

        merged = getattr(b, "_merged", 0)

        if getattr(b, "has_hotel", False):
            b.nr_pct = 1.0
            b.nr_adj_height = b.nr_pct * b.normalized_height
            print(f"NR pct overridden to 1.0 because full_nr or has_hotel is True ({b.short_alias})")
            continue

        if merged == 0:
            continue

        m_res = b._m_res
        m_res_empty = b._m_res_empty
        m_nr = b._m_nr
        m_nr_empty = b._m_nr_empty
        meter_total = b._meter_total

        # Borrow ratios if no meters
        if meter_total == 0 and not getattr(b, "_ratios_applied", False):
            x, y = b.geometry.centroid.x, b.geometry.centroid.y
            nearest_candidates = list(idx_rtree.nearest((x, y, x, y), 1))
            if nearest_candidates:
                neighbor = building_map[nearest_candidates[0]]
                r_res       = neighbor._m_res / neighbor._meter_total
                r_res_empty = neighbor._m_res_empty / neighbor._meter_total
                r_nr        = neighbor._m_nr / neighbor._meter_total
                r_nr_empty  = neighbor._m_nr_empty / neighbor._meter_total

                m_res       = round(merged * r_res)
                m_res_empty = round(merged * r_res_empty)
                m_nr        = round(merged * r_nr)
                m_nr_empty  = round(merged * r_nr_empty)

                b._ratios_applied = True
                print(f"[RATIO] {b.short_alias} used ratios from {neighbor.short_alias} (no meters found)")

            meter_total = m_res + m_res_empty + m_nr + m_nr_empty

        # Scale meters → proportional units
        if meter_total == 0:
            u_res = u_res_empty = u_nr = 0
            u_nr_empty = merged
        else:
            scale = merged / meter_total
            u_res = round(m_res * scale)
            u_res_empty = round(m_res_empty * scale)
            u_nr = round(m_nr * scale)
            u_nr_empty = round(m_nr_empty * scale)

            # Fix rounding drift
            diff = merged - (u_res + u_res_empty + u_nr + u_nr_empty)
            if diff != 0:
                largest = max(
                    ("u_res", u_res),
                    ("u_res_empty", u_res_empty),
                    ("u_nr", u_nr),
                    ("u_nr_empty", u_nr_empty),
                    key=lambda x: x[1]
                )[0]
                if largest == "u_res":
                    u_res += diff
                elif largest == "u_res_empty":
                    u_res_empty += diff
                elif largest == "u_nr":
                    u_nr += diff
                else:
                    u_nr_empty += diff

        # --- Assign units according to correct splitting ---
        # assign residential units
        b.units_res_primary = max(0, u_res)
        b.units_res_empty   = max(0, u_res_empty)
        b.units_res         = b.units_res_primary + b.units_res_empty

        # NR units (secondary only)
        b.units_nr_secondary = max(0, u_nr)
        b.units_nr_empty     = max(0, u_nr_empty)
        b.units_nr_secondary_str      = sum(len(addr.strs) for addr in b.addresses)
        b.units_nr_secondary_students = 0
        b.units_nr = b.units_est_merged - b.units_res

        b.total_units = (b.units_res or 0) + (b.units_nr or 0)

        # Calculate residential pct
        b.res_pct = ((b.units_res or 0) / b.total_units) if b.total_units else 0.0
        # Calculate NR pct
        b.nr_pct = ((b.units_nr or 0) / b.total_units) if b.total_units else 0.0
        print(f"Calculated nr_pct before override: {b.nr_pct:.2f}, has_hotel: {b.has_hotel}, short_alias: {b.short_alias}")

        if str(b.has_hotel).lower() in ("1", "true", "yes"):
            b.nr_pct = 1.0
            print(f"NR pct overridden to 1.0 because has_hotel is True")

        # Calculate empty pct
        b.empty_pct = ((b.units_res_empty or 0) + (b.units_nr_empty or 0)) / b.total_units if b.total_units else 0.0

        # Adjusted heights
        b.res_adj_height = (b.normalized_height or 0) * b.res_pct
        b.nr_adj_height = (b.normalized_height or 0) * b.nr_pct
        b.empty_adj_height = (b.normalized_height or 0) * b.empty_pct

        # Ensure nothing is None
        for attr in [
            "units_res_primary", "units_res_empty", "units_res",
            "units_nr_secondary", "units_nr_empty",
            "units_nr_secondary_str", "units_nr_secondary_students",
            "units_nr",
        ]:
            if getattr(b, attr) is None:
                setattr(b, attr, 0)

        if idx % 100 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Calculated units for {idx}/{len(all_buildings)} buildings")

    # ---------------------- Build audit CSV ----------------------
    print("[STEP] Building audit rows and saving CSV")
    audit_rows = []

    for idx, b in enumerate(all_buildings, 1):
        audit_rows.append({
            "short_alias": val_zero(b.short_alias, is_number=False),
            "building_id": val_zero(b.id),
            "type": (b.tp_cls.strip() if isinstance(b.tp_cls, str) and b.tp_cls.strip() else "none"),
            "height": val_zero(b.height),
            "norm_height": val_zero(b.normalized_height),
            "superficie": val_zero(b.superficie),
            "norm_superficie": val_zero(b.normalized_superficie),
            "floors_est": val_zero(b.floors_est),
            "units_est_meters": val_zero(b.units_est_meters),
            "units_est_volume": val_zero(b.units_est_volume),
            "units_est_merged": val_zero(b.units_est_merged),
            "pop_est": val_zero(b.pop_est),
            "full_nr?": int(getattr(b, "full_nr", 0)),
            "measured": int(getattr(b, "measured", 0)),
            "surveyed": int(getattr(b, "surveyed", 0)),

            # Residential units
            "units_res_primary": val_zero(getattr(b, "units_res_primary", 0)),
            "units_res_empty": val_zero(getattr(b, "units_res_empty", 0)),
            "units_res": val_zero(getattr(b, "units_res", 0)),

            # Non-residential units
            "units_nr_secondary": val_zero(getattr(b, "units_nr_secondary", 0)),
            "units_nr_empty": val_zero(getattr(b, "units_nr_empty", 0)),
            "units_nr_secondary_str": val_zero(getattr(b, "units_nr_secondary_str", 0)),
            "units_nr_secondary_students": val_zero(getattr(b, "units_nr_secondary_students", 0)),
            "units_nr": val_zero(getattr(b, "units_nr", 0)),

            # Percentages
            "res_pct": val_zero(getattr(b, "res_pct", 0)),
            "nr_pct": val_zero(getattr(b, "nr_pct", 0)),
            "empty_pct": val_zero(getattr(b, "empty_pct", 0)),

            # Adjusted heights
            "res_adj_height": val_zero(getattr(b, "res_adj_height", 0)),
            "nr_adj_height": val_zero(getattr(b, "nr_adj_height", 0)),
            "empty_adj_height": val_zero(getattr(b, "empty_adj_height", 0)),

            "geometry": val_zero(getattr(b, "geometry", None), is_number=False)
        })

    if idx % 100 == 0 or idx == len(all_buildings):
        print(f"[PROGRESS] Added {idx}/{len(all_buildings)} buildings to audit rows")

    audit_df = pd.DataFrame(audit_rows).sort_values("short_alias")
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_V4.csv")
    audit_df.to_csv(output_path, index=False)
    print(f"✅ V4 estimation completed and saved to {output_path} ({len(audit_rows)} buildings)")

    return ds
