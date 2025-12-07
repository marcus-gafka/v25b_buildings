import pandas as pd
import geopandas as gpd
from shapely import wkt
import os
from constants import ESTIMATES_CSV, ALIAS_CSV

OUTPUT_CSV = "final/merged_output.csv"
OUTPUT_GEOJSON = "final/merged_output.geojson"

RENAME_COLUMNS = {
    "TARGET_FID_12_13": "VPC_Building_ID",
    "full_alias": "V25B_Full_Alias",
    "short_alias": "V25B_Short_Alias",
    "Nome_Sesti": "VPC_Sestieri",
    "Qu_Terra": "VPC_Door_Height",
    "Superficie": "VPC_Footprint",
    "Dest_Ps_An": "VPC_City_Plan_Code",
    "Codice_Ses": "VPC_Sestieri_Code",
    "TipoFun": "VPC_Type_Function",
    "SpecFun": "VPC_Specific_Function",
    "Qu_Gronda": "VPC_Gutter_Height",
    "Xc": "VPC_Xc",
    "Yc": "VPC_Yc",
    "Perimetro": "VPC_Perimeter",
    "SEZ21_ID": "VPC_Census_ID",
    "Codice": "VPC_Island_Code",
    "POP21": "VPC_Census_Population",
    "FAM21": "VPC_Census_Families",
    "ABI21": "VPC_Census_Units",
    "EDI21": "VPC_Census_Buildings",
    "Nome_Isola": "VPC_Island_Name",
    "TP_CLS_ED": "VPC_Arch_Type",
    "DESC_TIPO": "VPC_Arch_Type_Desc",
    "height": "V25B_Height",
    "norm_height": "V25B_Normalized_Height",
    "norm_superficie": "V25B_Normalized_Footprint",
    "floors_est": "V25B_Est_Floors",
    "units_est_meters": "V25B_Units_Est_Meters",
    "units_est_volume": "V25B_Units_Est_Volume",
    "units_est_merged": "V25B_Est_Units",
    "pop_est": "V25B_Est_Population",
    "full_nr": "V25B_Est_Non_Res",
    "units_res_primary": "V25B_Est_Res_Primary",
    "units_res_empty": "V25B_Est_Res_Vacant",
    "units_res": "V25B_Est_Res_Units",
    "units_nr_secondary": "V25B_Est_Non_Res_Secondary",
    "units_nr_empty": "V25B_Est_Non_Res_Vacant",
    "units_nr_secondary_str": "V25B_STR",
    "units_nr_secondary_students": "V25B_Students",
    "units_nr": "V25B_Est_Non_Res_Units",
    "res_pct": "V25B_Est_Pct_Res",
    "nr_pct": "V25B_Est_Pct_Non_Res",
    "empty_pct": "V25B_Est_Pct_Vacant",
    "res_adj_height": "V25B_Est_Res_Height",
    "nr_adj_height": "V25B_Est_Non_Res_Height",
    "empty_adj_height": "V25B_Est_Vacant_Height",
    "measured": "V25B_Measured?",
    "surveyed": "V25B_Surveyed?",
    "geometry": "geometry",
}

# ------------------------------
# COLUMN ORDER
# Sensible order for analysis / export
# ------------------------------
COLUMN_ORDER = [
    "VPC_Building_ID",
    "V25B_Short_Alias",
    "V25B_Full_Alias",
    "VPC_Sestieri",
    "VPC_Sestieri_Code",
    "VPC_Island_Name",
    "VPC_Island_Code",
    "VPC_City_Plan_Code",
    "VPC_Type_Function",
    "VPC_Specific_Function",
    "VPC_Arch_Type",
    "VPC_Arch_Type_Desc",
    "VPC_Door_Height",
    "VPC_Gutter_Height",
    "VPC_Footprint",
    "V25B_Footprint",
    "V25B_Height",
    "V25B_Normalized_Height",
    "V25B_Normalized_Footprint",
    "V25B_Est_Floors",
    "V25B_Units_Est_Meters",
    "V25B_Units_Est_Volume",
    "V25B_Est_Units",
    "V25B_Est_Population",
    "V25B_Est_Res_Primary",
    "V25B_Est_Res_Vacant",
    "V25B_Est_Res_Units",
    "V25B_Est_Non_Res_Secondary",
    "V25B_Est_Non_Res_Vacant",
    "V25B_STR",
    "V25B_Students",
    "V25B_Est_Non_Res_Units",
    "V25B_Est_Non_Res",
    "V25B_Est_Pct_Res",
    "V25B_Est_Pct_Non_Res",
    "V25B_Est_Pct_Vacant",
    "V25B_Est_Res_Height",
    "V25B_Est_Non_Res_Height",
    "V25B_Est_Vacant_Height",
    "V25B_Measured?",
    "V25B_Surveyed?",
    "geometry",
]

def add_og_fields():
    print("📥 Loading CSVs...")
    esti = pd.read_csv(ESTIMATES_CSV)   # this CSV has building_id
    aliases = pd.read_csv(ALIAS_CSV)    # this CSV has TARGET_FID_12_13

    # clean weird spaces/BOM
    esti.columns = esti.columns.str.replace(r'[^0-9A-Za-z_]+', '', regex=True).str.strip()
    aliases.columns = aliases.columns.str.replace(r'[^0-9A-Za-z_]+', '', regex=True).str.strip()

    print("\nARCH COLUMNS:\n", aliases.columns.tolist())
    print("\nUNITS COLUMNS:\n", esti.columns.tolist())

    print("🔗 Merging on TARGET_FID_12_13 ↔ building_id...")
    merged = aliases.merge(
        esti,
        left_on="TARGET_FID_12_13",
        right_on="building_id",
        how="left"
    )

    # ------------------------------
    # OPTIONAL RENAME
    # ------------------------------
    if RENAME_COLUMNS:
        print("✏️ Renaming columns...")
        merged = merged.rename(columns=RENAME_COLUMNS)

    # ------------------------------
    # OPTIONAL REORDER
    # ------------------------------
    if COLUMN_ORDER:
        print("📑 Reordering columns...")
        final_cols = [c for c in COLUMN_ORDER if c in merged.columns]
        extras = [c for c in merged.columns if c not in final_cols]
        merged = merged[final_cols + extras]

    # ------------------------------
    # SAVE CSV
    # ------------------------------
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    print("💾 Writing CSV output...")
    merged.to_csv(OUTPUT_CSV, index=False)

    # ------------------------------
    # GEOJSON EXPORT
    # ------------------------------
    if "geometry" in merged.columns:
        print("🌍 Converting geometry (WKT → GeoDataFrame)...")
        # Safely convert non-empty geometry strings to shapely
        merged["geometry"] = merged["geometry"].apply(lambda x: wkt.loads(x) if pd.notna(x) and x.strip() else None)

        geo = gpd.GeoDataFrame(
            merged,
            geometry="geometry",
            crs="EPSG:4326"
        )

        os.makedirs(os.path.dirname(OUTPUT_GEOJSON), exist_ok=True)
        print("💾 Writing GeoJSON...")
        geo.to_file(OUTPUT_GEOJSON, driver="GeoJSON")
    else:
        print("⚠️ 'geometry' column not found — skipping GeoJSON export.")

    print("✅ Done! CSV + GeoJSON created.")

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    add_og_fields()
