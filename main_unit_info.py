from dataset import Dataset
from constants import ALIAS_GEOJSON, FILTERED_WATER_CSV
import pandas as pd
import os

print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
ds = Dataset(str(ALIAS_GEOJSON))

print("📂 Loading filtered water consumption CSV...")
water_df = pd.read_csv(FILTERED_WATER_CSV)
water_df["FID"] = water_df["FID"].astype(int)
water_df["Componenti"] = pd.to_numeric(water_df["Componenti"], errors='coerce').fillna(1)

# --- Build address -> list[(FID, Componenti)] mapping ---
address_meters_map = (
    water_df.groupby("ProcessedAddress")[["FID", "Componenti"]]
    .apply(lambda df: [(int(fid), int(comp)) for fid, comp in df.values])
    .to_dict()
)

print("📊 Computing units_est for ALL buildings...")

rows = []

# --- Loop through every building in Venice ---
for s in ds.venice.sestieri:
    for isl in s.islands:
        for tract in isl.tracts:
            for b in tract.buildings:

                total_units = 0

                # Fill meters + calculate units
                for addr in b.addresses:
                    addr_units = 0
                    new_meters = []

                    if addr.address in address_meters_map:
                        for fid, comp in address_meters_map[addr.address]:
                            addr_units += comp
                            new_meters.append(fid)

                    addr.meters = new_meters
                    total_units += addr_units

                b.units_est = total_units

                # --- Format helper ---
                def join_list(x):
                    if isinstance(x, list):
                        return ";".join(str(i) for i in x)
                    return ""

                # --- Build CSV row ---
                rows.append({
                    "short_alias": b.short_alias,
                    "building_id": b.id,

                    "num_addresses": len(b.addresses),
                    "addresses": ";".join(a.address for a in b.addresses),

                    "num_meters": sum(len(a.meters) for a in b.addresses),
                    "meters": ";".join(join_list(a.meters) for a in b.addresses),

                    "num_hotels": sum(len(a.hotels) for a in b.addresses),
                    "hotels": ";".join(join_list(a.hotels) for a in b.addresses),

                    "num_hotels_extras": sum(len(a.hotels_extras) for a in b.addresses),
                    "hotels_extras": ";".join(join_list(a.hotels_extras) for a in b.addresses),

                    "num_strs": sum(len(a.strs) for a in b.addresses),
                    "strs": ";".join(join_list(a.strs) for a in b.addresses),
                })

print("📄 Generating CSV...")

# Convert to DataFrame
out_df = pd.DataFrame(rows)

# Output in this directory
out_path = os.path.join(os.path.dirname(__file__), "unit_info.csv")

# Write CSV
out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print(f"✅ CSV written to: {out_path}")
print("🎉 Done!")
