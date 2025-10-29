import os
from datatypes import Dataset as ds
from plotter import Plotter as p
from file_utils import geojson_to_csv, add_alias_column
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary.geojson")
POSTALIAS_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary_with_alias.geojson")
POSTALIAS_CSV = os.path.join(DATA_DIR, "V25B_Buildings_Primary_with_alias.csv")

def analysis():
    """Load post-alias GeoJSON and plot buildings and snake."""
    if not os.path.exists(POSTALIAS_GEOJSON):
        raise FileNotFoundError("Post-alias GeoJSON not found. Run assign_aliases() first.")

    dataset = ds(POSTALIAS_GEOJSON, POSTALIAS_CSV)
    dataset.load_csv()
    dataset.build_hierarchy_with_alias()

    plotter = p(dataset.buildings)
    plotter.filter_buildings_by_alias("SP")
    plotter.plot_buildings_and_snake(group="island")

    # Print first 10 building aliases
    for b in dataset.buildings[:10]:
        print(b.alias, b.row)

if __name__ == "__main__":
    analysis()
