import string
import geopandas as gpd
from shapely.geometry import shape
from dataset import Dataset
from constants import FILTERED_GEOJSON, ALIAS_GEOJSON, ALIAS_CSV, BUILDING_FIELD

ALPHA = 0.3 # more directional 0 <- -> closer
BETA = 0.7 # more west 0 <- -> 1 more north

# === Helpers ===
def generate_letter_codes():
    """Generate A-Z, then AA-ZZ letter codes for tracts/buildings."""
    letters = list(string.ascii_uppercase)
    double_letters = [a + b for a in letters for b in letters]
    codes = letters + double_letters
    print(f"🔤 Generated {len(codes)} letter codes")
    return codes

def greedy_tsp(buildings):
    """
    Greedy TSP that starts at NW corner and selects next building
    based on a weighted combination of northwestness and distance.
    `buildings` is a list of tuples (building_obj, tract_obj)
    """
    if not buildings:
        return []

    # Extract centroids
    centroids = [(b, t, b.geometry.centroid) for b, t in buildings]

    # Start at north-west corner: max Y, min X
    start = max(centroids, key=lambda x: (x[2].y, -x[2].x))
    tour = [(start[0], start[1])]
    unvisited = [(b, t, p) for b, t, p in centroids if b != start[0]]
    current_point = start[2]

    x_max = max(p.x for _, _, p in centroids)
    y_max = max(p.y for _, _, p in centroids)

    while unvisited:
        scores = []
        for b, t, p in unvisited:
            westness = x_max - p.x      # bigger = more west
            northness = y_max - p.y     # bigger = more north
            direction_score = BETA * northness + (1 - BETA) * westness
            distance = current_point.distance(p)
            score = ALPHA * direction_score - (1 - ALPHA) * distance
            scores.append((score, b, t, p))

        # Pick building with highest combined score
        best = max(scores, key=lambda x: x[0])
        tour.append((best[1], best[2]))
        unvisited = [u for u in unvisited if u[0] != best[1]]
        current_point = best[3]

    return tour

# === Alias Assignment ===
def assign_aliases(dataset: Dataset, ALPHA=0.5):
    """Assign aliases using greedy TSP through island, ignoring tract boundaries."""
    letter_codes = generate_letter_codes()

    for s in dataset.venice.sestieri:
        for i in s.islands:
            # Assign tract letters first
            for t_idx, t in enumerate(i.tracts, start=1):
                tract_letter = letter_codes[t_idx - 1] if t_idx <= len(letter_codes) else f"T{t_idx}"
                t.full_alias = f"{s.code}-{i.code}-{tract_letter}"

            # Flatten all buildings for this island
            all_buildings = []
            for t in i.tracts:
                for b in t.buildings:
                    if b.geometry:
                        all_buildings.append((b, t))

            # Use greedy TSP ordering
            ordered_buildings = greedy_tsp(all_buildings)

            # Assign building numbers continuously
            for idx, (b, t) in enumerate(ordered_buildings, start=1):
                building_number = f"{idx:03d}"
                tract_letter = t.full_alias.split("-")[-1]
                b.full_alias = f"{s.code}-{i.code}-{tract_letter}-{building_number}"
                b.short_alias = f"{i.code}-{building_number}"

            print(f"🌴 {i.code} island: total buildings = {len(ordered_buildings)}")

# === Convert Buildings to GeoDataFrame ===
def buildings_to_gdf(dataset):
    rows = []
    for s in dataset.venice.sestieri:
        for island in s.islands:
            for tract in island.tracts:
                for b in tract.buildings:
                    if b.geometry:
                        rows.append({
                            "geometry": shape(b.geometry),
                            "full_alias": b.full_alias,
                            "short_alias": b.short_alias,
                            BUILDING_FIELD: b.id,
                            "tract_id": tract.id,
                            "island_code": island.code,
                            "sestiere_code": s.code,
                        })
    gdf = gpd.GeoDataFrame(rows, geometry=[row["geometry"] for row in rows], crs="EPSG:4326")
    return gdf

# === Merge aliases with original GeoDataFrame ===
def attach_aliases_to_original(original_gdf: gpd.GeoDataFrame, alias_gdf: gpd.GeoDataFrame):
    print("🔗 Attaching aliases to original data...")
    
    if BUILDING_FIELD not in alias_gdf.columns:
        raise KeyError(f"alias_gdf must have '{BUILDING_FIELD}' column to merge with original_gdf")
    if BUILDING_FIELD not in original_gdf.columns:
        raise KeyError(f"original_gdf must have '{BUILDING_FIELD}' column to merge")

    gdf = original_gdf.merge(
        alias_gdf[[BUILDING_FIELD, "full_alias", "short_alias"]],
        on=BUILDING_FIELD,
        how="left"
    )

    first_cols = [BUILDING_FIELD, "full_alias", "short_alias", "Nome_Sesti", "Codice"]
    remaining_cols = [c for c in gdf.columns if c not in first_cols + ["geometry"]]
    gdf_final = gdf[first_cols + remaining_cols + ["geometry"]]

    print(f"✅ Prepared final GDF with {len(gdf_final)} rows and {len(gdf_final.columns)} columns")
    return gdf_final

# === Main ===
def main():
    print(f"📂 Loading original GeoJSON: {FILTERED_GEOJSON}")
    original_gdf = gpd.read_file(FILTERED_GEOJSON)
    print(f"📊 Original buildings: {len(original_gdf)}")

    print("🧠 Building dataset hierarchy...")
    dataset = Dataset(FILTERED_GEOJSON)

    print("🏷️ Generating aliases directly in objects using greedy TSP...")
    assign_aliases(dataset, ALPHA=0.7)  # tune ALPHA here

    print("🗺️ Converting buildings to GeoDataFrame...")
    alias_gdf = buildings_to_gdf(dataset)

    print("🔗 Combining with original attributes...")
    final_gdf = attach_aliases_to_original(original_gdf, alias_gdf)

    print("💾 Saving results...")
    final_gdf.to_file(ALIAS_GEOJSON, driver="GeoJSON")
    final_gdf.drop(columns="geometry").to_csv(ALIAS_CSV, index=False)

    print("🏁 Done! Full copy with aliases created.")

if __name__ == "__main__":
    main()
