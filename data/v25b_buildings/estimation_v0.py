import pandas as pd
from file_utils import load_csv
from constants import (
    FILTERED_CSV,
    ESTIMATES_DIR,
)

HEIGHT_PER_FLOOR = 3.2
AVERAGE_UNIT_AREA = 125.0

def estimation_v0(ds, islands=None):

    bcsv = load_csv(FILTERED_CSV)
    building_map = {b.id: b for s in ds.venice.sestieri for i in s.islands for t in i.tracts for b in t.buildings}

    tract_building_counts = bcsv.groupby("SEZ21")["TARGET_FID_12_13"].count().to_dict()

    results = []
    
    for _, row in bcsv.iterrows():
        b_id = row["TARGET_FID_12_13"]
        building = building_map.get(b_id)
        if building is None:
            continue

        # island filter
        if islands and not any(building.short_alias.startswith(isl) for isl in islands):
            continue

        qu_terra = row["Qu_Terra"]
        qu_gronda = row["Qu_Gronda"]
        superficie = row["Superficie"]
        sez21 = row["SEZ21"]

        building.height = qu_gronda - qu_terra

        building.floors_est = max(1, int(round((qu_gronda - qu_terra) / HEIGHT_PER_FLOOR))) if pd.notnull(qu_terra) and pd.notnull(qu_gronda) else 1
        building.units_est_meters = sum(len(addr.meters) for addr in building.addresses)
        building.units_est_volume = int(round((building.floors_est * superficie) / AVERAGE_UNIT_AREA))

        n_blds = tract_building_counts.get(sez21, 1)
        pop_val = row["POP21"]
        building.pop_est = int(round(pop_val / n_blds)) if pd.notnull(pop_val) else 0

        results.append({
            "short_alias": building.short_alias,
            "building_id": building.id,

            "height": building.height,
            "superficie": building.superficie,

            "floors_est": building.floors_est,
            "units_est_meters": building.units_est_meters,
            "units_est_volume": building.units_est_volume,
            "pop_est": building.pop_est
        })

    # save CSV
    pd.DataFrame(results).to_csv(ESTIMATES_DIR / "VPC_Estimates_V0.csv", index=False)

    print(f"✅ V0 estimation populated for {len(building_map)} buildings")
    return ds