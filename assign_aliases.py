import string
import geopandas as gpd
from shapely.geometry import shape, Point
from dataset import Dataset
from constants import FILTERED_GEOJSON, ALIAS_GEOJSON, ALIAS_CSV, BUILDING_FIELD

# === Helpers ===
def generate_letter_codes():
    """Generate A-Z, then AA-ZZ letter codes for tracts/buildings."""
    letters = list(string.ascii_uppercase)
    double_letters = [a + b for a in letters for b in letters]
    codes = letters + double_letters
    print(f"🔤 Generated {len(codes)} letter codes")
    return codes

# === Alias Assignment ===
def assign_aliases(dataset: Dataset):
    """Assign aliases directly to each Building object in the hierarchy."""
    letter_codes = generate_letter_codes()

    for s_idx, s in enumerate(dataset.venice.sestieri, start=1):
        print(f"\n📦 Processing sestiere #{s_idx}: {s.name} (code={s.code}), islands={len(s.islands)}")

        for i_idx, i in enumerate(s.islands, start=1):
            total_buildings = sum(len(t.buildings) for t in i.tracts)
            print(f"  🌴 Island #{i_idx}: code={i.code}, tracts={len(i.tracts)}, buildings={total_buildings}")

            # Assign tract-level aliases
            for t_idx, t in enumerate(i.tracts, start=1):
                tract_letter = letter_codes[t_idx - 1] if t_idx <= len(letter_codes) else f"T{t_idx}"
                t.full_alias = f"{s.code}-{i.code}-{tract_letter}"

            # --- Assign building-level aliases across the entire island ---
            building_counter = 1  # Reset for each island
            for t in i.tracts:
                # Sort buildings within tract by X coordinate
                sorted_buildings = sorted(
                    t.buildings,
                    key=lambda b: b.centroid.x if b.centroid else 0
                )

                for b in sorted_buildings:
                    building_number = f"{building_counter:03d}"  # continuous numbering across tracts
                    # Keep tract_letter if you want it per tract, or remove if numbering is island-wide
                    t_letter = t.full_alias.split("-")[-1]  # get tract letter
                    b.full_alias = f"{s.code}-{i.code}-{t_letter}-{building_number}"
                    b.short_alias = f"{i.code}-{building_number}"
                    building_counter += 1
                    #print(f"    🏠 Building {b.id}: {b.full_alias}")

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
    """Attach aliases from the Building objects GeoDataFrame to the original GeoDataFrame using BUILDING_FIELD."""
    print("🔗 Attaching aliases to original data...")
    
    if BUILDING_FIELD not in alias_gdf.columns:
        raise KeyError(f"alias_gdf must have '{BUILDING_FIELD}' column to merge with original_gdf")
    if BUILDING_FIELD not in original_gdf.columns:
        raise KeyError(f"original_gdf must have '{BUILDING_FIELD}' column to merge")

    # Merge on BUILDING_FIELD
    gdf = original_gdf.merge(
        alias_gdf[[BUILDING_FIELD, "full_alias", "short_alias"]],
        on=BUILDING_FIELD,
        how="left"
    )

    # Reorder columns if desired
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

    print("🏷️ Generating aliases directly in objects...")
    assign_aliases(dataset)

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
