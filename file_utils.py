import json
import pandas as pd
from pathlib import Path
from shapely import wkt
from shapely.geometry import mapping

# === Load / Save JSON ===

def load_geojson(path: str) -> dict:
    """Load a GeoJSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_geojson(data: dict, path: str):
    """Save a dictionary as GeoJSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"💾 GeoJSON saved to {path}")

def load_csv(path: str) -> dict:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    required_cols = ["TARGET_FID_12_13", "Qu_Terra", "Qu_Gronda", "POP21", "Superficie", "SEZ21"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"❌ CSV must include '{col}' field.")
    return df

def geojson_to_csv(features, csv_path: str, column_order=None):
    """Convert GeoJSON features into a CSV table."""
    rows = []
    for f in features:
        props = f.get("properties", {}).copy()
        if "geometry" in f:
            props["geometry"] = f["geometry"]
        rows.append(props)

    df = pd.DataFrame(rows)

    # Reorder columns if needed
    if column_order:
        existing_cols = [c for c in column_order if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in existing_cols]
        df = df[existing_cols + remaining_cols]

    df.to_csv(csv_path, index=False)
    print(f"💾 CSV saved to {csv_path}")

def csv_to_geojson(csv_path: str, geometry_column="geometry", save: bool = True):

    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    features = []

    for _, row in df.iterrows():
        props = row.to_dict()

        # Extract geometry
        geom = props.pop(geometry_column, None)
        if isinstance(geom, str):
            try:
                # Convert WKT to shapely geometry
                geom_obj = wkt.loads(geom)
                # Convert shapely geometry to GeoJSON dict
                geom = mapping(geom_obj)
            except Exception as e:
                print(f"[WARN] Failed to parse geometry: {e}")
                geom = None
        else:
            geom = None

        feature = {
            "type": "Feature",
            "properties": props,
            "geometry": geom
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    if save:
        output_path = csv_path.with_suffix(".geojson")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        print(f"💾 GeoJSON saved to {output_path}")

    return geojson
