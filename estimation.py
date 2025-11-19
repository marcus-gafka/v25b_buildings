import pandas as pd
from dataset import Dataset
from datatypes import Building
from constants import FILTERED_WATER_CSV, FILTERED_ADDRESS_CSV, ALIAS_GEOJSON
from plotter import plot_island_by_tpcls

# --- Load CSVs ---
print("📂 Loading filtered water consumption CSV...")
water_df = pd.read_csv(FILTERED_WATER_CSV)
print(f"  Loaded {len(water_df)} water meter entries.")

print("📂 Loading filtered addresses CSV...")
address_df = pd.read_csv(FILTERED_ADDRESS_CSV)
print(f"  Loaded {len(address_df)} address entries.")

# --- Standardize addresses ---
water_df["ProcessedAddress"] = water_df["ProcessedAddress"].astype(str).str.strip().str.upper()
address_df["Full_sesti"] = address_df["Full_sesti"].astype(str).str.strip().str.upper()

# --- Count meters per address ---
meters_per_address = water_df.groupby("ProcessedAddress").size().to_dict()
print(f"  Found {len(meters_per_address)} unique addresses with meters.")

# --- Map addresses to building IDs ---
address_df["meters"] = address_df["Full_sesti"].map(meters_per_address).fillna(0).astype(int)
meters_per_building = address_df.groupby("TARGET_FID_12_13")["meters"].sum().to_dict()
print(f"  Computed meters per building for {len(meters_per_building)} buildings.")

# --- Load dataset ---
print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
ds = Dataset(str(ALIAS_GEOJSON))

# --- Update units_est for each building ---
print("📊 Updating units_est from CSV data...")
for sest in ds.venice.sestieri:
    for isl in sest.islands:
        for tract in isl.tracts:
            for b in tract.buildings:
                b_id = getattr(b, "id", None)
                if b_id in meters_per_building:
                    b.units_est = int(meters_per_building[b_id])
                    print(f"  Building {b.short_alias} ({b_id}) → units_est = {b.units_est}")
                else:
                    b.units_est = 0
                    print(f"  Building {b.short_alias} ({b_id}) → units_est = 0 (no meters found)")

# --- Plot one island as example ---
print("📊 Plotting buildings for island MELO...")
plot_island_by_tpcls(ds, "BOLD")

print("✅ Units estimation complete.")
