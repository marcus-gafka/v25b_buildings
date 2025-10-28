import json
import matplotlib.pyplot as plt
from shapely.geometry import shape

# --- Load GeoJSON file ---
GEOJSON_FILE = "V25B_Buildings_Primary_Building_Dataset.geojson"

with open(GEOJSON_FILE) as f:
    data = json.load(f)

# --- Get list of unique sestiere, ignore None ---
sestieres = list({feature["properties"]["Nome_Sesti"] for feature in data["features"] if feature["properties"].get("Nome_Sesti")})
sestieres.sort()

# --- Assign a color to each sestiere ---
colors = {}
cmap = plt.cm.get_cmap("tab20", len(sestieres))
for i, sest in enumerate(sestieres):
    colors[sest] = cmap(i)

# --- Plot buildings ---
fig, ax = plt.subplots()
for feature in data["features"]:
    geom = shape(feature["geometry"])
    sest = feature["properties"].get("Nome_Sesti")
    color = colors.get(sest, "gray")  # fallback for None or unknown

    # Handle polygons and multipolygons
    if geom.geom_type == "Polygon":
        x, y = geom.exterior.xy
        ax.fill(x, y, color=color, alpha=0.6, edgecolor="black", linewidth=0.3)
    elif geom.geom_type == "MultiPolygon":
        for poly in geom.geoms:
            x, y = poly.exterior.xy
            ax.fill(x, y, color=color, alpha=0.6, edgecolor="black", linewidth=0.3)

# --- Add legend ---
handles = [plt.Line2D([0], [0], color=colors[s], lw=4, alpha=0.6) for s in sestieres]
ax.legend(handles, sestieres, title="Sestiere", loc="upper right")

# --- Style plot ---
ax.set_aspect("equal", adjustable="box")
ax.grid(True, linestyle="--", linewidth=0.5)
plt.title("Building Footprints by Sestiere")
plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.show()
