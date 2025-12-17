import os
import pandas as pd
import numpy as np
from rtree import index
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
ALPHA_MERGE = 0.6

# ------------------------------------------------------------
# UTILITY FUNCTIONS
# ------------------------------------------------------------

def val_zero(x, is_number=True):
    """Return 0 or empty string if value is None."""
    if x is None:
        return 0 if is_number else ""
    return x

# ------------------------------------------------------------
# UNITS FROM WATER METERS
# ------------------------------------------------------------

def calc_units_from_meter_data(building, meter_df):
    """
    Calculate building units from water meter readings.
    Filters out public usage and non-relevant meters.
    """
    total_units = 0
    for addr in building.addresses:
        addr_meters = meter_df[meter_df["ProcessedAddress"] == addr.address]
        filtered = addr_meters[addr_meters["Condominio"] != "X"]
        filtered = filtered[filtered["Cat_Tariffa"].str.strip().str.lower() != "uso pubblico"]

        for _, row in filtered.iterrows():
            multiplier = row["Componenti"] if pd.notna(row["Componenti"]) and row["Componenti"] != "" else 1
            subtotal = row[["Nuclei_domestici", "Nuclei_commerciali", "Nuclei_non_residenti"]].sum()
            total_units += subtotal * multiplier
    return int(total_units)

# ------------------------------------------------------------
# HEIGHT & SUPERFICIE NORMALIZATION
# ------------------------------------------------------------

def set_normalized_height_and_superficie(building, all_buildings, k=K_NEIGHBORS, debug=False):
    """
    Compute normalized height and surface area for a building.
    Falls back to neighbors if direct values are missing.
    """
    if building.qu_terra is None:
        building.qu_terra = 0

    building.normalized_height = _compute_normalized_height(building, all_buildings, k)
    building.normalized_superficie = _compute_normalized_superficie(building, all_buildings, k)

def _compute_normalized_height(building, all_buildings, k):
    """Compute normalized height using neighbors if qu_gronda is missing."""
    if building.qu_gronda not in [None, 0, 9999]:
        building.height = building.qu_gronda - building.qu_terra
        return building.height

    neighbors = [
        b for b in all_buildings
        if b != building and getattr(b, "island", None) == getattr(building, "island", None)
        and b.qu_gronda not in [None, 0, 9999]
    ]
    if neighbors:
        neighbors = sorted(neighbors, key=lambda b2: building.centroid.distance(b2.centroid))[:k]
        avg_qu_gronda = np.mean([b2.qu_gronda for b2 in neighbors])
        building.height = 0
        return round(avg_qu_gronda - building.qu_terra, 2)
    return 0

def _compute_normalized_superficie(building, all_buildings, k):
    """Compute normalized superficie using neighbors if missing or out of bounds."""
    if building.superficie is not None and 0 < building.superficie < 30000:
        return building.superficie
    neighbors = [b for b in all_buildings if b != building and b.superficie is not None and 0 < b.superficie < 30000]
    if neighbors:
        neighbors = sorted(neighbors, key=lambda b2: building.centroid.distance(b2.centroid))[:k]
        return round(np.mean([b2.superficie for b2 in neighbors]), 2)
    return 0

# ------------------------------------------------------------
# NON-RESIDENTIAL (NR) INFO
# ------------------------------------------------------------

def is_full_nr(tipofun, specfun, dest, tp_cls, has_hotel, pop21, abi21, edi21):
    """
    Determine if a building is fully non-residential (NR) based on multiple criteria.
    Returns (bool, list of reasons).
    """
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
    """
    Attach non-residential info and measured/survey flags to all buildings.
    """
    unit_info_df = pd.read_csv(UNIT_INFO_CSV)
    survey_df = pd.read_csv(FILTERED_SURVEY_CSV)
    field_df = pd.read_csv(TOTAL_FIELDWORK_CSV)
    uninhabited_df = pd.read_csv(UNINHABITED_CSV)

    uninhabited_aliases = set(uninhabited_df["full_alias"].astype(str).str.upper().str.strip())
    unit_info_df["short_alias"] = unit_info_df["short_alias"].str.upper()
    survey_df["short_alias"] = survey_df["short_alias"].str.upper()
    field_df["short_alias"] = field_df["short_alias"].str.upper()

    units_str_map = dict(zip(unit_info_df["short_alias"], unit_info_df.get("num_strs", [0]*len(unit_info_df))))
    units_empty_map = dict(zip(unit_info_df["short_alias"], unit_info_df.get("num_zero_consumption_meters", [0]*len(unit_info_df))))
    measured_map = dict(zip(field_df["short_alias"], field_df.get("Measured Height", [np.nan]*len(field_df))))
    surveyed_set = set(survey_df["short_alias"])

    all_tracts = [t for s in ds.venice.sestieri for isl in s.islands for t in isl.tracts]

    for t in all_tracts:
        for b in t.buildings:
            sha = (b.short_alias or "").strip().upper()
            fa = (b.full_alias or "").strip().upper()

            b.units_str = int(units_str_map.get(sha, 0))
            b.units_empty = int(units_empty_map.get(sha, 0))
            b.measured = pd.notna(measured_map.get(sha, None))
            b.surveyed = sha in surveyed_set

            nr_flag, nr_reasons = is_full_nr(b.tipo_fun, b.spec_fun, b.dest_pt_an, b.tp_cls, b.has_hotel, t.pop21, t.abi21, t.edi21)
            csv_flag = fa in uninhabited_aliases
            if csv_flag:
                nr_reasons.append("listed in Uninhabited CSV")
            b.full_nr = nr_flag or csv_flag

# ------------------------------------------------------------
# ESTIMATION V4
# ------------------------------------------------------------

def estimation_v4(ds, islands=None, debug=False):
    """
    Main function to compute building floor, unit, NR allocations and produce audit CSV.
    """
    print("[STEP] Attaching NR info")
    attach_nr_info(ds)

    all_buildings = _get_all_buildings(ds, islands)
    print(f"[INFO] Total buildings to process: {len(all_buildings)}")

    bcsv, meter_df, linreg_df, linreg_map = _load_csvs()
    _assign_building_types(all_buildings, bcsv)
    _compute_building_metrics(all_buildings, linreg_df, linreg_map, meter_df, debug)
    _allocate_units_and_population(all_buildings, bcsv)
    idx_rtree, building_map = _build_meter_index(all_buildings, meter_df)
    _assign_proportional_units(all_buildings, idx_rtree, building_map)
    _build_audit_csv(all_buildings)

    return ds

# ------------------------------------------------------------
# HELPER FUNCTIONS FOR ESTIMATION_V4
# ------------------------------------------------------------

def _get_all_buildings(ds, islands):
    """Flatten all buildings in dataset, optionally filtering by islands."""
    buildings = []
    for s in ds.venice.sestieri:
        for i in s.islands:
            if islands and not any(i.code.startswith(isl) for isl in islands):
                continue
            for t in i.tracts:
                buildings.extend(t.buildings)
    return buildings

def _load_csvs():
    """Load CSV files and build linear regression map."""
    bcsv = pd.read_csv(FILTERED_CSV)
    meter_df = pd.read_csv(FILTERED_WATER_CSV)
    linreg_df = pd.read_csv(LIN_REG_CSV)
    linreg_map = {row["TP_CLS_ED"]: row for _, row in linreg_df.iterrows()}
    return bcsv, meter_df, linreg_df, linreg_map

def _assign_building_types(all_buildings, bcsv):
    """Assign building type from CSV lookup."""
    bcsv_by_id = bcsv.set_index("TARGET_FID_12_13")
    for idx, b in enumerate(all_buildings, 1):
        b.tp_cls = bcsv_by_id.loc[b.id].get("TP_CLS_ED", "unknown") if b.id in bcsv_by_id.index else "unknown"
        if idx % 100 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Assigned type to {idx}/{len(all_buildings)} buildings")

# ------------------------------------------------------------
# Compute building metrics: normalized height, superficie, floors, units, liveable space
# ------------------------------------------------------------
def _compute_building_metrics(all_buildings, linreg_df, linreg_map, meter_df, debug=False):
    """
    Compute building metrics: normalized height, floors estimation, units from meters,
    liveable space.
    """
    for idx, b in enumerate(all_buildings, 1):
        set_normalized_height_and_superficie(b, all_buildings, debug=debug)

        # Floors estimation
        row = linreg_map.get(b.tp_cls)
        model = row if row is not None and row.get("qu_count", 0) >= 10 else linreg_df.iloc[-1]
        m_qu = model.get("m_qu")
        b_qu = model.get("b_qu")
        gf_qu = model.get("ground_floor_qu", 2.0)

        b.floors_est = max(1, int(round(m_qu * (b.normalized_height or 0) + b_qu)))
        b.ground_floor_height = gf_qu
        b.upper_floors_height = (b.normalized_height or 0) - b.ground_floor_height

        b.units_est_meters = calc_units_from_meter_data(b, meter_df)
        b.liveable_space = max(0, (b.floors_est - 1) * (b.normalized_superficie or 0))

        if idx % 50 == 0 or idx == len(all_buildings):
            print(f"[PROGRESS] Computed metrics for {idx}/{len(all_buildings)} buildings")

# ------------------------------------------------------------
# Allocate units and population per tract
# ------------------------------------------------------------
def _allocate_units_and_population(all_buildings, bcsv):
    """
    Allocate population and units per tract based on liveable space,
    considering NR and RES buildings.
    """
    bcsv_by_id = bcsv.set_index("TARGET_FID_12_13")
    bcsv_by_tract = bcsv.set_index("SEZ21")

    tract_map = {}
    for b in all_buildings:
        if b.id in bcsv_by_id.index:
            tract_id = bcsv_by_id.loc[b.id].get("SEZ21")
            tract_map.setdefault(tract_id, []).append(b)

    for tract_id, buildings in tract_map.items():
        # Tract totals
        if tract_id in bcsv_by_tract.index:
            row = bcsv_by_tract.loc[tract_id]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            pop_total = int(row.get("POP21", 0))
            unit_total = int(row.get("ABI21", 0))
        else:
            pop_total = 0
            unit_total = 0

        nr_buildings = [b for b in buildings if getattr(b, "full_nr", False)]
        res_buildings = [b for b in buildings if not getattr(b, "full_nr", False)]

        # NR buildings get zero residential allocation
        for b in nr_buildings:
            b.pop_est = 0
            b.units_est_volume = 0
            b.units_est_merged = 0
            b.units_est_meters = 0

        if not res_buildings:
            continue

        total_liveable = sum(b.liveable_space or 0 for b in res_buildings)
        if total_liveable == 0:
            for b in res_buildings:
                b.pop_est = 0
                b.units_est_volume = 0
                b.units_est_merged = 0
            continue

        # Population allocation
        raw_pop = [(b, (b.liveable_space / total_liveable) * pop_total) for b in res_buildings]
        for b, v in raw_pop:
            b.pop_est = int(v)
        remainder_pop = pop_total - sum(b.pop_est for b, _ in raw_pop)
        frac_pop = sorted(raw_pop, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_pop):
            frac_pop[i % len(frac_pop)][0].pop_est += 1

        # Volume units allocation
        raw_units = [(b, (b.liveable_space / total_liveable) * unit_total) for b in res_buildings]
        for b, v in raw_units:
            b.units_est_volume = int(v)
        remainder_units = unit_total - sum(b.units_est_volume for b, _ in raw_units)
        frac_units = sorted(raw_units, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_units):
            frac_units[i % len(frac_units)][0].units_est_volume += 1

        # Merged units allocation
        raw_merged = [(b, ALPHA_MERGE * b.units_est_meters + (1 - ALPHA_MERGE) * b.units_est_volume) for b in res_buildings]
        for b, v in raw_merged:
            b.units_est_merged = int(v)
        remainder_merged = unit_total - sum(b.units_est_merged for b, _ in raw_merged)
        frac_merged = sorted(raw_merged, key=lambda x: (x[1] - int(x[1])), reverse=True)
        for i in range(remainder_merged):
            frac_merged[i % len(frac_merged)][0].units_est_merged += 1

# ------------------------------------------------------------
# Build meter index for spatial neighbor lookups
# ------------------------------------------------------------
def _build_meter_index(all_buildings, meter_df):
    """
    Build spatial index (R-tree) and prepare meter lookup lists per address.
    Returns R-tree index and building map.
    """
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

    return idx_rtree, building_map

# ------------------------------------------------------------
# Assign proportional units and adjust heights/liveable space
# ------------------------------------------------------------
def _assign_proportional_units(all_buildings, idx_rtree, building_map):
    """
    Assign proportional units per building based on meters and merged units,
    apply NR/res/empty percentages, compute adjusted heights and liveable spaces.
    """
    for idx, b in enumerate(all_buildings, 1):
        merged = getattr(b, "_merged", 0)

        if getattr(b, "has_hotel", False):
            b.nr_pct = 1.0
            b.nr_adj_height = b.nr_pct * b.normalized_height
            continue

        if merged == 0:
            continue

        m_res, m_res_empty, m_nr, m_nr_empty = b._m_res, b._m_res_empty, b._m_nr, b._m_nr_empty
        meter_total = b._meter_total

        # Borrow ratios from neighbor if no meters
        if meter_total == 0 and not getattr(b, "_ratios_applied", False):
            x, y = b.geometry.centroid.x, b.geometry.centroid.y
            nearest_candidates = list(idx_rtree.nearest((x, y, x, y), 1))
            if nearest_candidates:
                neighbor = building_map[nearest_candidates[0]]
                r_res = neighbor._m_res / neighbor._meter_total
                r_res_empty = neighbor._m_res_empty / neighbor._meter_total
                r_nr = neighbor._m_nr / neighbor._meter_total
                r_nr_empty = neighbor._m_nr_empty / neighbor._meter_total

                m_res = round(merged * r_res)
                m_res_empty = round(merged * r_res_empty)
                m_nr = round(merged * r_nr)
                m_nr_empty = round(merged * r_nr_empty)

                b._ratios_applied = True
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
            diff = merged - (u_res + u_res_empty + u_nr + u_nr_empty)
            if diff != 0:
                largest = max([("u_res", u_res), ("u_res_empty", u_res_empty), ("u_nr", u_nr), ("u_nr_empty", u_nr_empty)], key=lambda x: x[1])[0]
                if largest == "u_res":
                    u_res += diff
                elif largest == "u_res_empty":
                    u_res_empty += diff
                elif largest == "u_nr":
                    u_nr += diff
                else:
                    u_nr_empty += diff

        # Assign units and percentages
        b.units_res_primary = max(0, u_res)
        b.units_res_empty = max(0, u_res_empty)
        b.units_res = b.units_res_primary + b.units_res_empty

        b.units_nr_secondary = max(0, u_nr)
        b.units_nr_empty = max(0, u_nr_empty)
        b.units_nr = b.units_est_merged - b.units_res

        b.total_units = (b.units_res or 0) + (b.units_nr or 0)
        b.res_pct = ((b.units_res or 0) / b.total_units) if b.total_units else 0.0
        b.nr_pct = ((b.units_nr or 0) / b.total_units) if b.total_units else 0.0
        b.empty_pct = ((b.units_res_empty or 0) + (b.units_nr_empty or 0)) / b.total_units if b.total_units else 0.0

        b.res_adj_height = (b.normalized_height or 0) * b.res_pct
        b.nr_adj_height = (b.normalized_height or 0) * b.nr_pct
        b.empty_adj_height = (b.normalized_height or 0) * b.empty_pct

        b.upperonly_res_adj_height = (b.upper_floors_height or 0) * b.res_pct
        b.upperonly_nr_adj_height = (b.upper_floors_height or 0) * b.nr_pct
        b.upperonly_empty_adj_height = (b.upper_floors_height or 0) * b.empty_pct

        b.res_liveable_space = b.liveable_space * b.res_pct
        b.nr_liveable_space = b.liveable_space * b.nr_pct

# ------------------------------------------------------------
# Build audit CSV
# ------------------------------------------------------------
def _build_audit_csv(all_buildings):
    """Generate audit CSV for all buildings."""
    audit_rows = []
    for idx, b in enumerate(all_buildings, 1):
        audit_rows.append({
            "building_id": val_zero(b.id),
            "full_alias": val_zero(getattr(b, "full_alias", None), is_number=False),
            "short_alias": val_zero(getattr(b, "short_alias", None), is_number=False),
            "qu_terra": val_zero(getattr(b, "qu_terra", 0)),
            "qu_gronda": val_zero(getattr(b, "qu_gronda", 0)),
            "tp_cls": (b.tp_cls.strip() if isinstance(b.tp_cls, str) and b.tp_cls.strip() else "none"),
            "tipo_fun": val_zero(getattr(b, "tipo_fun", None), is_number=False),
            "spec_fun": val_zero(getattr(b, "spec_fun", None), is_number=False),
            "dest_pt_an": val_zero(getattr(b, "dest_pt_an", None), is_number=False),
            "height": val_zero(getattr(b, "height", 0)),
            "superficie": val_zero(getattr(b, "superficie", 0)),
            "normalized_height": val_zero(getattr(b, "normalized_height", 0)),
            "normalized_superficie": val_zero(getattr(b, "normalized_superficie", 0)),
            "floors_est": val_zero(getattr(b, "floors_est", 0)),
            "units_est_meters": val_zero(getattr(b, "units_est_meters", 0)),
            "units_est_volume": val_zero(getattr(b, "units_est_volume", 0)),
            "units_est_merged": val_zero(getattr(b, "units_est_merged", 0)),
            "pop_est": val_zero(getattr(b, "pop_est", 0)),
            "full_nr?": int(getattr(b, "full_nr", 0)),
            "livable_space": val_zero(getattr(b, "liveable_space", 0)),
            "res_livable_space": val_zero(getattr(b, "res_liveable_space", 0)),
            "nr_livable_space": val_zero(getattr(b, "nr_liveable_space", 0)),
            "ground_floor_height": val_zero(getattr(b, "ground_floor_height", 0)),
            "upper_floors_height": val_zero(getattr(b, "upper_floors_height", 0)),
            "units_res": val_zero(getattr(b, "units_res", 0)),
            "units_res_empty": val_zero(getattr(b, "units_res_empty", 0)),
            "units_res_primary": val_zero(getattr(b, "units_res_primary", 0)),
            "units_nr": val_zero(getattr(b, "units_nr", 0)),
            "units_nr_empty": val_zero(getattr(b, "units_nr_empty", 0)),
            "units_nr_secondary": val_zero(getattr(b, "units_nr_secondary", 0)),
            "res_pct": val_zero(getattr(b, "res_pct", 0)),
            "nr_pct": val_zero(getattr(b, "nr_pct", 0)),
            "empty_pct": val_zero(getattr(b, "empty_pct", 0)),
            "res_adj_height": val_zero(getattr(b, "res_adj_height", 0)),
            "nr_adj_height": val_zero(getattr(b, "nr_adj_height", 0)),
            "empty_adj_height": val_zero(getattr(b, "empty_adj_height", 0)),
            "upperonly_res_adj_height": val_zero(getattr(b, "upperonly_res_adj_height", 0)),
            "upperonly_nr_adj_height": val_zero(getattr(b, "upperonly_nr_adj_height", 0)),
            "upperonly_empty_adj_height": val_zero(getattr(b, "upperonly_empty_adj_height", 0)),
            "measured": int(getattr(b, "measured", 0)),
            "surveyed": int(getattr(b, "surveyed", 0)),
            "geometry": val_zero(getattr(b, "geometry", None), is_number=False),
        })

    audit_df = pd.DataFrame(audit_rows).sort_values("short_alias")
    output_path = os.path.join(ESTIMATES_DIR, "VPC_Estimates_V4-new.csv")
    audit_df.to_csv(output_path, index=False)
    print(f"✅ Audit CSV saved to {output_path} ({len(audit_rows)} buildings)")
