import json
import csv
import os
import ast  # safely parse stringified Python lists like [[12.3, 45.6]]

def geojson_to_csv(geojson_file: str):
    """Convert GeoJSON to CSV (flattening geometry and preserving all properties)."""
    with open(geojson_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    all_keys = set()
    for feat in features:
        all_keys.update(feat.get("properties", {}).keys())
    all_keys = sorted(all_keys)
    all_keys += ["geometry_type", "geometry_coordinates"]

    base, _ = os.path.splitext(geojson_file)
    output_file = base + ".csv"

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=all_keys)
        writer.writeheader()
        for feat in features:
            row = feat.get("properties", {}).copy()
            geom = feat.get("geometry", {})
            row["geometry_type"] = geom.get("type")
            # serialize coords as compact JSON
            row["geometry_coordinates"] = json.dumps(geom.get("coordinates", []))
            writer.writerow(row)

    print(f"✅ CSV saved to {output_file}")
    return output_file


def csv_to_geojson(csv_file: str, output_file: str):
    """Rebuild GeoJSON from a CSV that was generated using geojson_to_csv()."""
    features = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            geom_type = row.pop("geometry_type", None)
            coords_str = row.pop("geometry_coordinates", "[]")

            # Parse coordinates safely
            try:
                coords = json.loads(coords_str)
            except json.JSONDecodeError:
                try:
                    coords = ast.literal_eval(coords_str)
                except Exception:
                    coords = []

            # Remove empty strings so numbers and nulls aren’t mixed
            properties = {k: (v if v != "" else None) for k, v in row.items()}

            features.append({
                "type": "Feature",
                "properties": properties,
                "geometry": {
                    "type": geom_type or "Polygon",
                    "coordinates": coords
                }
            })

    geojson_data = {"type": "FeatureCollection", "features": features}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2, ensure_ascii=False)

    print(f"✅ GeoJSON saved to {output_file}")
    return output_file

def add_alias_column(csv_file: str, buildings: list, alias_column_name: str = "ALIAS"):
    """
    Add a new column to an existing CSV with building aliases.
    Saves the updated CSV as a new file ending with '_with_alias.csv'.

    Args:
        csv_file: path to the input CSV
        buildings: list of Building objects, in the same order as the CSV rows
        alias_column_name: name of the new column to add
    """
    # Read existing CSV
    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = list(csv.reader(f))
        header = reader[0]
        rows = reader[1:]

    # Insert new column at position 1 (after the first column)
    header.insert(1, alias_column_name)
    for i, row in enumerate(rows):
        if i < len(buildings):
            row.insert(1, buildings[i].alias)
        else:
            row.insert(1, "")

    # Generate output filename
    base, ext = os.path.splitext(csv_file)
    output_file = f"{base}_with_alias{ext}"

    # Write updated CSV
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Updated CSV saved with column '{alias_column_name}' as {output_file}")
    return output_file

