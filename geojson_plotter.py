import json
import matplotlib.pyplot as plt
from shapely.geometry import shape

# --- Load GeoJSON file ---
GEOJSON_FILE = "V25B_Buildings_Primary_Building_Dataset.geojson"

with open(GEOJSON_FILE) as f:
    data = json.load(f)

# --- Extract building geometries ---
fig, ax = plt.subplots()
for feature in data["features"]:
    geom = shape(feature["geometry"])

    # Handle polygons and multipolygons
    if geom.geom_type == "Polygon":
        x, y = geom.exterior.xy
        ax.plot(x, y, color="black", linewidth=0.5)
    elif geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            x, y = poly.exterior.xy
            ax.plot(x, y, color="black", linewidth=0.5)

# --- Style plot ---
ax.set_aspect("equal", adjustable="box")
ax.grid(True, linestyle="--", linewidth=0.5)
plt.title("Building Footprints")
plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.show()