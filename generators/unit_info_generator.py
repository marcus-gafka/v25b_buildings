import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from dataset import Dataset
from constants import ALIAS_GEOJSON, FILTERED_WATER_CSV, UNIT_INFO_CSV
import pandas as pd

print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
ds = Dataset(str(ALIAS_GEOJSON))

print("📂 Loading filtered water consumption CSV...")
water_df = pd.read_csv(FILTERED_WATER_CSV)
water_df["FID"] = water_df["FID"].astype(int)
water_df["Componenti"] = pd.to_numeric(water_df["Componenti"], errors='coerce').fillna(1)

# Add consumption column as numeric
water_df["Consumo_medio_2024"] = pd.to_numeric(
    water_df["Consumo_medio_2024"], errors="coerce"
).fillna(0)

# --- Build mappings ---
address_meters_map = (
    water_df.groupby("ProcessedAddress")[["FID", "Componenti"]]
    .apply(lambda df: [(int(fid), int(comp)) for fid, comp in df.values])
    .to_dict()
)

# FID -> Consumo_medio_2024 map
fid_consumption_map = dict(zip(water_df["FID"], water_df["Consumo_medio_2024"]))

print("📊 Computing units_est for ALL buildings...")

rows = []

# --- Loop through every building ---
for s in ds.venice.sestieri:
    for isl in s.islands:
        for tract in isl.tracts:
            for b in tract.buildings:

                total_units = 0
                zero_consumption_count = 0

                for addr in b.addresses:
                    addr_units = 0
                    new_meters = []

                    if addr.address in address_meters_map:
                        for fid, comp in address_meters_map[addr.address]:
                            addr_units += comp
                            new_meters.append(fid)

                            # Count low-consumption meters
                            consumo = fid_consumption_map.get(fid, 0)
                            if consumo < 0.5:
                                zero_consumption_count += 1

                    addr.meters = new_meters
                    total_units += addr_units

                b.units_est = total_units

                def join_list(x):
                    if isinstance(x, list):
                        return ";".join(str(i) for i in x)
                    return ""

                rows.append({
                    "short_alias": b.short_alias,
                    "building_id": b.id,

                    "num_addresses": len(b.addresses),
                    "addresses": ";".join(a.address for a in b.addresses),

                    "num_meters": sum(len(a.meters) for a in b.addresses),
                    "meters": ";".join(join_list(a.meters) for a in b.addresses),

                    "num_zero_consumption_meters": zero_consumption_count,

                    "num_hotels": sum(len(a.hotels) for a in b.addresses),
                    "hotels": ";".join(join_list(a.hotels) for a in b.addresses),

                    "num_hotels_extras": sum(len(a.hotels_extras) for a in b.addresses),
                    "hotels_extras": ";".join(join_list(a.hotels_extras) for a in b.addresses),

                    "num_strs": sum(len(a.strs) for a in b.addresses),
                    "strs": ";".join(join_list(a.strs) for a in b.addresses),
                })

print("📄 Generating CSV...")

out_df = pd.DataFrame(rows)

# 🔠 Sort alphabetically by short_alias
out_df = out_df.sort_values("short_alias")

out_df.to_csv(UNIT_INFO_CSV, index=False, encoding="utf-8-sig")

print(f"✅ CSV written to: {UNIT_INFO_CSV}")
print("🎉 Done!")

