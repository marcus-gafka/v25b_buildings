from dataset import Dataset
from constants import ALIAS_GEOJSON
from plotter import plot_island_by_tpcls_filtered

# --- Load dataset ---
print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
ds = Dataset(str(ALIAS_GEOJSON))

# --- List of islands to plot ---
my_islands = ["TOLE","ROMA"]

# --- Plot each island using the helper ---
for island_code in my_islands:
    print(f"📊 Plotting island {island_code}...")
    plot_island_by_tpcls_filtered(ds, island_code)

print("✅ Script complete.")
