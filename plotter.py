import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import geopandas as gpd
from shapely.geometry import Point, LineString
from dataset import Dataset
import pandas as pd
import matplotlib.colors as mcolors

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
            geom = b.geometry or (b.centroid if isinstance(b.centroid, Point) else None)
            if geom is None:
                continue  # skip buildings with no geometry

            rows.append({
                "geometry": geom,
                "short_alias": b.short_alias or "",
                "tract_id": tract.id,
                "floors_est": b.floors_est,
                "units_est_meters": b.units_est_meters,
                "units_est_volume": b.units_est_volume,
                "pop_est": b.pop_est,
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

    # --- Add labels with floors, units (meters), units (volume), pop ---
    for idx, row in gdf.iterrows():
        if row["short_alias"]:
            centroid = row.geometry.centroid
            label = f"{row['floors_est']},{row['units_est_meters']},{row['units_est_volume']},{row['pop_est']}"
            ax.text(
                centroid.x,
                centroid.y,
                label,
                fontsize=8,
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

def plot_island_by_tpcls_filtered(dataset: Dataset, island_code: str, figsize=(12, 12)):
    # --- Load CSV/GeoJSON safely ---
    try:
        df = pd.read_csv(dataset.source, dtype=str)
    except pd.errors.ParserError:
        df = gpd.read_file(dataset.source)

    if "short_alias" not in df.columns or "TP_CLS_ED" not in df.columns:
        raise ValueError("File must have 'short_alias' and 'TP_CLS_ED' columns.")

    df = df[["short_alias", "TP_CLS_ED"]].drop_duplicates().set_index("short_alias")

    colored_codes = [
        "Nr","B1","Kna","SM","Ka","Knt","Kot","P","SP",
        "Nd","Ne","Or","SU","fa"
    ]

    cmap = plt.cm.get_cmap("tab20", len(colored_codes))
    tp_color_map = {code: cmap(i) for i, code in enumerate(colored_codes)}

    WHITE = (1, 1, 1, 1)

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

    # --- Prepare building rows ---
    rows = []
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

    if not rows:
        print(f"No building geometries found for island {island_code}")
        return

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # --- Apply fixed colors (others = white) ---
    gdf["color"] = gdf["tp"].apply(lambda tp: tp_color_map.get(tp, WHITE))

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.5)

    # --- Label units ---
    for _, row in gdf.iterrows():
        if row["short_alias"]:
            c = row.geometry.centroid
            ax.text(
                c.x,
                c.y,
                row["short_alias"][-3:],
                fontsize=5,
                ha="center",
                va="center",
                color="black"
            )

    # --- Legend (placed outside the plot area) ---
    legend_elements = [
        Patch(
            facecolor=tp_color_map[tp],
            edgecolor="black",
            label=f"{tp}: {mcolors.to_hex((tp_color_map[tp]))}"
        )
        for tp in colored_codes
    ]

    # Place legend to the right of the plot
    ax.legend(
        handles=legend_elements,
        title="TP_CLS_ED",
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=True
    )

    ax.set_title(f"Island {island_code} — Filtered TP_CLS_ED Colors", fontsize=16)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()

def plot_sestiere_w_str(dataset: Dataset, sestiere_code: str, figsize=(14, 14)):
    # --- Find sestiere ---
    sestiere = None
    for s in dataset.venice.sestieri:
        if s.code.upper() == sestiere_code.upper():
            sestiere = s
            break

    if not sestiere:
        raise ValueError(f"Sestiere '{sestiere_code}' not found.")

    # --- Prepare all buildings ---
    rows = []
    total_strs = 0
    total_hotels = 0
    total_hotels_extras = 0

    for isl in sestiere.islands:
        for tract in isl.tracts:
            for b in tract.buildings:
                geom = b.geometry or b.centroid
                if geom is None:
                    continue

                building_strs = 0
                building_hotels = 0
                building_hotels_extras = 0

                for addr in b.addresses:
                    if getattr(addr, "strs", None):
                        building_strs += len(addr.strs)
                    if getattr(addr, "hotels", None):
                        building_hotels += len(addr.hotels)
                    if getattr(addr, "hotels_extras", None):
                        building_hotels_extras += len(addr.hotels_extras)

                total_strs += building_strs
                total_hotels += building_hotels
                total_hotels_extras += building_hotels_extras

                rows.append({
                    "geometry": geom,
                    "short_alias": b.short_alias or "",
                    "str_count": building_strs
                })

    print(f"📊 Sestiere {sestiere_code} totals — STRs: {total_strs}, Hotels: {total_hotels}, Hotels Extras: {total_hotels_extras}")

    if not rows:
        print(f"No buildings found for sestiere {sestiere_code}")
        return

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

    # --- Colors ---
    WHITE = (1, 1, 1, 1)
    STR_COLOR = (1.0, 0.2, 0.2, 1.0)  # bright red

    gdf["color"] = gdf["str_count"].apply(lambda n: STR_COLOR if n >= 1 else WHITE)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=figsize)
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="black", linewidth=0.4)

    # --- Add STR labels only to highlighted buildings ---
    for _, row in gdf.iterrows():
        if row["str_count"] >= 1:
            c = row.geometry.centroid
            ax.text(
                c.x,
                c.y,
                str(row["str_count"]),
                fontsize=8,
                ha="center",
                va="center",
                color="black",
                fontweight="bold"
            )

    ax.set_title(f"Sestiere {sestiere_code} — STR Distribution", fontsize=18)
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()
