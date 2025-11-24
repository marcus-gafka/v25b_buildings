from dataset import Dataset
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from constants import RAW_GEOJSON, FILTERED_CSV, BUILDING_FIELD
import pandas as pd
from copy import deepcopy

KEEP_FIELDS = [
    "Qu_Terra",
    "Tipologia",
    "Qu_Gronda",
    "SEZ21",
    "POP21",
    "TP_CLS_ED",
    BUILDING_FIELD,
]

def filter_fields(dataset: Dataset, keep_fields: list) -> Dataset:
    """
    Return a new Dataset containing only properties in keep_fields.
    """
    filtered_features = []

    for feature in dataset.features:
        props = feature.get("properties", {})

        # Keep ONLY the listed fields (except geometry)
        new_props = {
            k: props.get(k, None)
            for k in keep_fields
            if k in props or k == BUILDING_FIELD
        }

        filtered_feature = {
            "type": feature.get("type", "Feature"),
            "properties": new_props,
            "geometry": feature.get("geometry"),
        }

        filtered_features.append(filtered_feature)

    filtered_dataset = deepcopy(dataset)
    filtered_dataset.features = filtered_features
    return filtered_dataset

def main():
    print("📂 Loading raw GeoJSON...")
    dataset = Dataset(RAW_GEOJSON)

    print("🧹 Filtering fields...")
    filtered_dataset = filter_fields(dataset, KEEP_FIELDS)

    # -------------------------
    # CSV OUTPUT ONLY
    # -------------------------
    print("💾 Saving CSV with BUILDING_FIELD first...")

    rows = []
    for f in filtered_dataset.features:
        props = f.get("properties", {}).copy()
        props["geometry"] = f.get("geometry")     # keep geometry in CSV if helpful
        rows.append(props)

    df = pd.DataFrame(rows)

    # Force BUILDING_FIELD to be first column
    columns = [BUILDING_FIELD] + [c for c in df.columns if c != BUILDING_FIELD]
    df = df[columns]

    df.to_csv(FILTERED_CSV, index=False)
    print(f"📄 CSV saved to: {FILTERED_CSV}")

    print("✅ Filtering complete (CSV only). No GeoJSON written.")

if __name__ == "__main__":
    main()