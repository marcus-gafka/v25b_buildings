import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import shape, Point
from dataset import Dataset

def plot_island(dataset: Dataset, island_code: str, figsize=(12, 12)):
    # --- Find the island ---
    island = None
    for s in dataset.venice.sestieri:
        for i in s.islands:
            if i.code == island_code:
                island = i
                break
        if island:
            break

    if not island:
        raise ValueError(f"Island code '{island_code}' not found.")

    # --- Prepare data for plotting ---
    rows = []
    tract_ids = []

    for tract in island.tracts:
        for b in tract.buildings:
            geom = None
            # Prefer full geometry, fallback to centroid
            if b.geometry:
                geom = b.geometry
            elif b.centroid:
                geom = b.centroid if isinstance(b.centroid, Point) else Point(b.centroid.x, b.centroid.y)
            else:
                continue  # skip buildings with no geometry

            rows.append({
                "geometry": geom,
                "short_alias": b.short_alias or "",  # fallback if None
                "tract_id": tract.id
            })
            tract_ids.append(tract.id)

    if not rows:
        print(f"No building geometries found for island {island_code}")
        return

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    # --- Assign colors per tract ---
    unique_tracts = sorted(list(set(tract_ids)))
    cmap = plt.cm.get_cmap("tab20", len(unique_tracts))
    tract_color_map = {tid: cmap(i) for i, tid in enumerate(unique_tracts)}
    gdf["color"] = gdf["tract_id"].map(tract_color_map)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

    # --- Add labels ---
    for idx, row in gdf.iterrows():
        if row["short_alias"]:  # only label if alias exists
            centroid = row.geometry.centroid
            ax.text(
                centroid.x,
                centroid.y,
                row["short_alias"],
                fontsize=6,
                ha="center",
                va="center",
                color="black"
            )

    ax.set_title(f"Island {island_code}", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()