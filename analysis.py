import os
from datatypes import Dataset as ds
from plotter import Plotter as p
from file_utils import geojson_to_csv, add_alias_column
import json
from estimation import estimate_population, estimate_all
from data_utils import return_estimated_population, return_actual_population

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary.geojson")
POSTALIAS_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary_with_alias.geojson")
POSTALIAS_CSV = os.path.join(DATA_DIR, "V25B_Buildings_Primary_with_alias.csv")

# USER INPUTS ---------------
filter_to = ""
group_by = "island"
#----------------------------

def analysis():
    """Load post-alias GeoJSON and plot buildings and snake."""
    if not os.path.exists(POSTALIAS_GEOJSON):
        raise FileNotFoundError("Post-alias GeoJSON not found. Run assign_aliases() first.")

    dataset = ds(POSTALIAS_GEOJSON, POSTALIAS_CSV)
    dataset.load_csv()
    dataset.build_hierarchy_with_alias()

    estimate_all(dataset, method="v0")  # for perfect totals
    print(return_estimated_population(dataset.sestieres))
    print(return_actual_population(dataset.sestieres))

    estimate_all(dataset, method="v1")  # for proportional estimates
    print(return_estimated_population(dataset.sestieres))
    print(return_actual_population(dataset.sestieres))

    plotter = p(dataset.buildings)
    plotter.filter_buildings_by_alias(filter_to)

    # --- PRINT BUILDING INFO ---
    print(f"\nBuildings starting with '{filter_to}':")
    for b in plotter.filtered_buildings:
        print(f"{b.alias:10} | Height: {b.height:<6.2f} | Footprint: {b.footprint:<8.2f} | Typology: {b.typology:<10} | Est: {b.pop_est:.2f}")
    print(f"Total buildings found: {len(plotter.filtered_buildings)}\n")
    # ---------------------------

    # plotter.plot_buildings_and_snake(group_by)
    plotter.plot_population_overlay()

if __name__ == "__main__":
    analysis()
