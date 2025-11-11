import geopandas as gpd

# === CONFIG ===
GEOJSON_PATH = "data/VPC_Buildings_With_Aliases.geojson"
FIELD = "short_alias"

# === LOAD GEOJSON ===
print(f"📂 Loading {GEOJSON_PATH}...")
gdf = gpd.read_file(GEOJSON_PATH)
print(f"✅ Loaded {len(gdf)} features.")

# === CHECK FOR DUPLICATES ===
if FIELD not in gdf.columns:
    print(f"❌ Field '{FIELD}' not found in GeoJSON columns:")
    print(gdf.columns)
else:
    duplicates = gdf[gdf.duplicated(subset=FIELD, keep=False)]
    count = len(duplicates)

    if count == 0:
        print(f"✅ No duplicates found in field '{FIELD}'.")
    else:
        print(f"⚠️ Found {count} duplicates in field '{FIELD}':")
        print(duplicates[[FIELD]].value_counts().head(10))
