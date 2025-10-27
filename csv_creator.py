import json
import csv

#check if git link is good

# --- Input and output file names ---
GEOJSON_FILE = "V25B_Buildings_Primary_Building_Dataset.geojson"
CSV_FILE = "buildings.csv"

# --- Load GeoJSON file ---
with open(GEOJSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# --- Open CSV file for writing ---
with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
    # Collect all property keys (for column headers)
    property_keys = set()
    for feature in data["features"]:
        property_keys.update(feature.get("properties", {}).keys())

    # Define CSV headers
    headers = ["id"] + list(property_keys) + ["geometry_type", "coordinates"]

    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()

    # --- Write each feature ---
    for i, feature in enumerate(data["features"], start=1):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        row = {
            "id": i,
            "geometry_type": geom.get("type", ""),
            "coordinates": json.dumps(geom.get("coordinates", [])),
        }
        # Add all property values
        for key in property_keys:
            row[key] = props.get(key, "")
        writer.writerow(row)

print(f"✅ CSV created: {CSV_FILE}")