import json
from pathlib import Path

# Input and output paths
INPUT_GEOJSON = "estimates/VPC_Estimates_V4.geojson"
OUTPUT_RES = "final/output_residential.geojson"
OUTPUT_NR = "final/output_nonresidential.geojson"
OUTPUT_EMPTY = "final/output_empty.geojson"

# Fields to filter
FIELDS = {
    "res_pct": OUTPUT_RES,
    "nr_pct": OUTPUT_NR,
    "empty_pct": OUTPUT_EMPTY,
}

def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_geojson(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def filter_features(features, field):
    """
    Keep features where 0 < field <= 1
    """
    filtered = []
    for feat in features:
        val = feat.get("properties", {}).get(field)
        if isinstance(val, (int, float)) and 0 < val <= 1:
            filtered.append(feat)
    return filtered

def main():
    if not Path(INPUT_GEOJSON).exists():
        print(f"❌ Input not found: {INPUT_GEOJSON}")
        return

    data = load_geojson(INPUT_GEOJSON)
    features = data.get("features", [])

    for field, out_path in FIELDS.items():
        filtered = filter_features(features, field)
        out_data = {
            "type": "FeatureCollection",
            "features": filtered,
        }
        save_geojson(out_path, out_data)
        print(f"✅ {field}: {len(filtered)} features → {out_path}")

if __name__ == "__main__":
    main()