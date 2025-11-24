from dataset import Dataset
from constants import ALIAS_GEOJSON, FILTERED_WATER_CSV
import pandas as pd
from plotter import plot_island_by_tpcls_filtered

print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
ds = Dataset(str(ALIAS_GEOJSON))

print("📂 Loading filtered water consumption CSV...")
water_df = pd.read_csv(FILTERED_WATER_CSV)
water_df["FID"] = water_df["FID"].astype(int)
water_df["Componenti"] = pd.to_numeric(water_df["Componenti"], errors='coerce').fillna(1)

# --- Create mapping: address -> list of (FID, Componenti) ---
address_meters_map = (
    water_df.groupby("ProcessedAddress")[["FID", "Componenti"]]
    .apply(lambda df: [(int(fid), int(comp)) for fid, comp in df.values])
    .to_dict()
)

print("📊 Computing units_est from Building.addresses[].meters (using Componenti)...")

# --- Loop through buildings and compute units_est ---
all_buildings = []

for s in ds.venice.sestieri:
    for isl in s.islands:
        for tract in isl.tracts:
            for b in tract.buildings:
                all_buildings.append(b)

                total_units = 0
                for addr in b.addresses:
                    # Compute total units for this address
                    addr_units = 0
                    new_meters = []
                    if addr.address in address_meters_map:
                        for fid, comp in address_meters_map[addr.address]:
                            addr_units += comp
                            new_meters.append(fid)
                    addr.meters = new_meters  # keep FIDs for each meter
                    total_units += addr_units

                b.units_est = total_units

print(f"✅ Updated units_est for {len(all_buildings)} buildings.")

# ---------------------------------------------------
# --- Filter for island "GHET" ---
# ---------------------------------------------------
print("\n🔎 Showing all buildings on island GHET:\n")

for s in ds.venice.sestieri:
    for isl in s.islands:
        if isl.code.upper() == "GHET" or isl.name.upper() == "GHET":
            for tract in isl.tracts:
                for b in tract.buildings:
                    print("─────────────────────────────────────────────")
                    print(f"🏛️  Building ID: {b.id}, Alias: {b.full_alias} / {b.short_alias}")
                    print(f"Units Estimated (by meters * Componenti): {b.units_est}")
                    print(f"Addresses: {len(b.addresses)}")

                    for addr in b.addresses:
                        print(f"  - Address: {addr.address}")
                        print(f"      meters: {addr.meters}")
                        print(f"      hotels: {addr.hotels}")
                        print(f"      hotels_extras: {addr.hotels_extras}")
                        print(f"      strs: {addr.strs}")

print("─────────────────────────────────────────────\n")

# ---------------------------------------------------
# --- Optional: plot the island ---
# ---------------------------------------------------
# print("📊 Plotting buildings for island 'GHET'...")
# plot_island_by_tpcls_filtered(ds, "GHET")

print("✅ Script complete.")
