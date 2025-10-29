import os
from datatypes import Dataset as ds
from plotter import Plotter as p
from file_utils import geojson_to_csv, add_alias_column
import json

# --- File paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary.geojson")
POSTALIAS_GEOJSON = os.path.join(DATA_DIR, "V25B_Buildings_Primary_with_alias.geojson")

def assign_aliases():
    """Generate building aliases and save updated CSV and GeoJSON with aliases."""
    # Convert raw GeoJSON to CSV
    csv_file = geojson_to_csv(RAW_GEOJSON)

    # Build dataset and hierarchy
    dataset = ds(RAW_GEOJSON)
    dataset.build_hierarchy()  # assigns b.alias for all buildings

    # Save CSV with alias
    add_alias_column(csv_file, dataset.buildings)

    # Save GeoJSON with alias
    with open(POSTALIAS_GEOJSON, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": dataset.features}, f, indent=2)

    print(f"Post-alias files saved:\nCSV: {csv_file}\nGeoJSON: {POSTALIAS_GEOJSON}")

if __name__ == "__main__":
    assign_aliases()
