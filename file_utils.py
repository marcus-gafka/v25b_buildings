import json
import pandas as pd

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


# === CSV Export ===

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
