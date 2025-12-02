import pandas as pd
from constants import ESTIMATES_DIR

def estimation_null(ds, islands=None):

    results = []

    for s in ds.venice.sestieri:
        for i in s.islands:
            for t in i.tracts:
                for b in t.buildings:

                    # optional island filter
                    if islands and not any(b.short_alias.startswith(isl) for isl in islands):
                        continue

                    # set all estimates to 0
                    b.floors_est = 0
                    b.units_est_meters = 0
                    b.units_est_volume = 0
                    b.pop_est = 0

                    results.append({
                        "short_alias": b.short_alias,
                        "building_id": b.id,
                        "height": b.height,
                        "superficie": b.superficie,
                        "floors_est": b.floors_est,
                        "units_est_meters": b.units_est_meters,
                        "units_est_volume": b.units_est_volume,
                        "pop_est": b.pop_est
                    })

    # save CSV
    pd.DataFrame(results).to_csv(ESTIMATES_DIR / "VPC_Estimates_Null.csv", index=False)

    print(f"✅ Null estimation complete for {len(results)} buildings (all estimates set to 0)")
    return ds
