import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point, LineString
from dataset import Dataset
import pandas as pd

def plot_island_by_tract(dataset: Dataset, island_code: str, figsize=(12, 12)):
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
    #gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

    # --- Add labels ---
    for idx, row in gdf.iterrows():
        if row["short_alias"]:  # only label if alias exists
            centroid = row.geometry.centroid
            ax.text(
                centroid.x,
                centroid.y,
                row["short_alias"][-3:],
                fontsize=10,
                ha="center",
                va="center",
                color="black"
            )

    ax.set_title(f"Island {island_code}", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()
    
def plot_island_bw(dataset: Dataset, island_code: str, figsize=(12, 12), show=True):
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
            if b.geometry:
                geom = b.geometry
            elif b.centroid:
                geom = b.centroid
            else:
                continue

            rows.append({
                "geometry": geom,
                "short_alias": b.short_alias or "",
                "tract_id": tract.id
            })
            tract_ids.append(tract.id)

    if not rows:
        print(f"No building geometries found for island {island_code}")
        return

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color="white", edgecolor="black", linewidth=0.5)

    for _, row in gdf.iterrows():
        if row["short_alias"]:
            centroid = row.geometry.centroid
            ax.text(
                centroid.x, centroid.y,
                row["short_alias"][-3:],
                fontsize=10, ha="center", va="center", color="black"
            )

    ax.set_title(f"Island {island_code}", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()

    if show:
        plt.show()

    return fig, ax

def plot_island_with_snake(dataset: Dataset, island_code: str, alias_field="short_alias"):
    # === Extract buildings for this island ===
    rows = []
    for s in dataset.venice.sestieri:
        for island in s.islands:
            if island.code == island_code:
                for tract in island.tracts:
                    for b in tract.buildings:
                        if b.geometry is not None and getattr(b, alias_field, None):
                            rows.append({
                                "short_alias": b.short_alias,
                                "full_alias": b.full_alias,
                                "geometry": b.geometry,
                                "centroid": b.centroid
                            })

    if not rows:
        print(f"⚠️ No buildings found for island '{island_code}'")
        return

    # === Convert to GeoDataFrame ===
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # === Sort by alias suffix ===
    gdf["suffix"] = gdf[alias_field].str[-3:].astype(int)
    gdf_sorted = gdf.sort_values("suffix")

    # === Create snake line ===
    centroids = gdf_sorted["centroid"].tolist()
    snake = LineString(centroids)

    # === Plot ===
    fig, ax = plt.subplots(figsize=(8, 8))
    gdf.plot(ax=ax, color="lightgray", edgecolor="black")
    centroids_gdf = gpd.GeoDataFrame(geometry=gdf_sorted["centroid"], crs=gdf.crs)
    centroids_gdf.plot(ax=ax, color="red", markersize=10)
    x, y = snake.xy
    ax.plot(x, y, color="blue", linewidth=2)

    # Add labels (optional)
    for _, row in gdf_sorted.iterrows():
        ax.text(row.centroid.x, row.centroid.y, str(row.suffix),
                fontsize=7, ha="center", va="center")

    ax.set_title(f"Island '{island_code}' Snake Path")
    ax.axis("equal")
    plt.show()

def plot_island_building_info(dataset: Dataset, island_code: str, figsize=(12, 12)):
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

    # --- Prepare data ---
    rows = []
    tract_ids = []

    for tract in island.tracts:
        for b in tract.buildings:
            geom = b.geometry or b.centroid
            if geom is None:
                continue

            rows.append({
                "geometry": geom,
                "tract_id": tract.id,
                #"label": f"{b.floors_est},{b.units_est},{b.pop_est}"
                "label": f"{b.units_est}"
            })
            tract_ids.append(tract.id)

    if not rows:
        print(f"No building geometries found for island {island_code}")
        return

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # --- Assign colors per tract ---
    unique_tracts = sorted(set(tract_ids))
    cmap = plt.cm.get_cmap("tab20", len(unique_tracts))
    tract_color_map = {tid: cmap(i) for i, tid in enumerate(unique_tracts)}
    gdf["color"] = gdf["tract_id"].map(tract_color_map)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

    # --- Add labels ---
    for _, row in gdf.iterrows():
        centroid = row.geometry.centroid
        ax.text(
            centroid.x,
            centroid.y,
            row["label"],
            fontsize=8,
            ha="center",
            va="center",
            color="black"
        )

    ax.set_title(f"Island {island_code} Buildings (Floors,Units,Pop)", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()

def plot_island_by_tpcls(dataset: Dataset, island_code: str, figsize=(12, 12)):
    # --- Load CSV/GeoJSON safely ---
    try:
        df = pd.read_csv(dataset.source, dtype=str)
    except pd.errors.ParserError:
        df = gpd.read_file(dataset.source)

    if "short_alias" not in df.columns or "TP_CLS_ED" not in df.columns:
        raise ValueError("File must have 'short_alias' and 'TP_CLS_ED' columns.")

    # Map short_alias → TP_CLS_ED
    df = df[["short_alias", "TP_CLS_ED"]].drop_duplicates().set_index("short_alias")

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

    # --- Prepare building data ---
    rows = []
    tpvals = []

    for tract in island.tracts:
        for b in tract.buildings:
            geom = b.geometry or b.centroid
            if geom is None:
                continue

            alias = b.short_alias or ""
            tp = df.loc[alias, "TP_CLS_ED"] if alias in df.index else "Unknown"

            rows.append({
                "geometry": geom,
                "tp": tp,
                "short_alias": alias,
                "units_est": b.units_est or 0
            })
            tpvals.append(tp)

    if not rows:
        print(f"No building geometries found for island {island_code}")
        return

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # --- Assign colors based on TP_CLS_ED ---
    unique_tp = sorted(set(tpvals))
    cmap = plt.cm.get_cmap("tab20", len(unique_tp))
    tp_color_map = {tp: cmap(i) for i, tp in enumerate(unique_tp)}
    gdf["color"] = gdf["tp"].map(tp_color_map)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

    # --- Add labels (units_est) ---
    for _, row in gdf.iterrows():
        if row["short_alias"]:
            c = row.geometry.centroid
            ax.text(
                c.x,
                c.y,
                f"{row['units_est']}",
                fontsize=9,
                ha="center",
                va="center",
                color="black"
            )

    ax.set_title(f"Island {island_code} — Colored by TP_CLS_ED", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()