import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from constants import ESTIMATES_CSV, ALIAS_CSV

import pandas as pd
import geopandas as gpd
from shapely import wkt
import os

OUTPUT_CSV = "final/V25B_Estimates_Final.csv"
OUTPUT_GEOJSON = "final/V25B_Estimates_Final.geojson"

# ------------------------------
# RENAME MAP
# ------------------------------
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
    #"TP_CLS_ED": "VPC_Arch_Type",
    "tp_cls": "VPC_Arch_Type",
    "DESC_TIPO": "VPC_Arch_Type_Desc",

    # V25B fields
    "height": "V25B_Height",
    "norm_height": "V25B_Normalized_Height",
    "norm_superficie": "V25B_Normalized_Footprint",
    "floors_est": "V25B_Est_Floors",
    "units_est_meters": "V25B_Units_Est_byMeters",
    "units_est_volume": "V25B_Units_Est_byVolume",
    "units_est_merged": "V25B_Est_Units_Merged",
    "pop_est": "V25B_Est_Population",

    "full_nr": "V25B_Full_NR?",
    "units_res_primary": "V25B_Est_Res_Primary",
    "units_res_empty": "V25B_Est_Res_Vacant",
    "units_res": "V25B_Est_Res_Units",
    "units_nr_secondary": "V25B_Est_NR_Secondary",
    "units_nr_empty": "V25B_Est_NR_Vacant",
    "units_nr_secondary_str": "V25B_STR",
    "units_nr_secondary_students": "V25B_Students",
    "units_nr": "V25B_Est_NR_Units",

    "res_pct": "V25B_Est_Pct_Res",
    "nr_pct": "V25B_Est_Pct_NR",
    "empty_pct": "V25B_Est_Pct_Vacant",

    "res_adj_height": "V25B_Est_Res_Height",
    "nr_adj_height": "V25B_Est_NR_Height",
    "empty_adj_height": "V25B_Est_Vacant_Height",

    "upperonly_res_adj_height": "V25B_Est_Res_UpperOnly_Height",
    "upperonly_nr_adj_height": "V25B_Est_NR_UpperOnly_Height",
    "upperonly_empty_adj_height": "V25B_Est_Vacant_UpperOnly_Height",

    "ground_floor_height": "V25B_Est_Ground_Floor_Height",
    "upper_floors_height": "V25B_Est_Upper_Floors_Height",

    "measured": "V25B_Measured?",
    "surveyed": "V25B_Surveyed?",
    "geometry": "geometry",
}

# ------------------------------
# OUTPUT ORDER
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
    "V25B_Height",
    "V25B_Normalized_Height",
    "V25B_Normalized_Footprint",
    "VPC_Census_Buildings",
    "VPC_Census_Units",
    "VPC_Census_Families",
    "VPC_Census_Population",
    "VPC_Census_ID",
    "V25B_Full_NR?",
    "V25B_Est_Floors",
    "V25B_Est_Units_byMeters",
    "V25B_Est_Units_byVolume",
    "V25B_Est_Units_Merged",
    "V25B_Est_Population",
    "V25B_Est_Res_Primary",
    "V25B_Est_Res_Vacant",
    "V25B_Est_Res_Units",
    "V25B_Est_NR_Secondary",
    "V25B_Est_NR_Vacant",
    "V25B_Est_NR_STR",
    "V25B_Est_NR_Students",
    "V25B_Est_NR_Units",
    "V25B_Est_Pct_Res",
    "V25B_Est_Pct_NR",
    "V25B_Est_Pct_Vacant",
    "V25B_Est_Res_Height",
    "V25B_Est_NR_Height",
    "V25B_Est_Vacant_Height",
    "V25B_Est_Res_UpperOnly_Height",
    "V25B_Est_NR_UpperOnly_Height",
    "V25B_Est_Vacant_UpperOnly_Height",
    "V25B_Est_Ground_Floor_Height",
    "V25B_Est_Upper_Floors_Height",
    "V25B_Measured?",
    "V25B_Surveyed?",
    "geometry",
]


# ------------------------------
# MAIN PROCESS
# ------------------------------
def add_og_fields():
    print("📥 Loading CSVs...")
    esti = pd.read_csv(ESTIMATES_CSV)
    aliases = pd.read_csv(ALIAS_CSV)

    esti.columns = esti.columns.str.replace(r'[^0-9A-Za-z_]+', '', regex=True).str.strip()
    aliases.columns = aliases.columns.str.replace(r'[^0-9A-Za-z_]+', '', regex=True).str.strip()

    print("🔗 Merging on TARGET_FID_12_13 ↔ building_id...")
    merged = aliases.merge(
        esti,
        left_on="TARGET_FID_12_13",
        right_on="building_id",
        how="left"
    )

    # RENAME
    print("✏️ Renaming columns...")
    merged = merged.rename(columns=RENAME_COLUMNS)

    # ENFORCE ORDER
    print("📑 Reordering columns...")
    final_cols = [c for c in COLUMN_ORDER if c in merged.columns]
    merged = merged[final_cols]

    # SAVE CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    print("💾 Writing CSV output...")
    merged.to_csv(OUTPUT_CSV, index=False)

    # GEOJSON
    if "geometry" in merged.columns:
        print("🌍 Converting geometry...")
        merged["geometry"] = merged["geometry"].apply(
            lambda x: wkt.loads(x) if isinstance(x, str) and x.strip() else None
        )
        geo = gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")

        os.makedirs(os.path.dirname(OUTPUT_GEOJSON), exist_ok=True)
        print("💾 Writing GeoJSON...")

        dupes = geo.columns[geo.columns.duplicated()].tolist()
        print("DUPLICATE COLUMNS:", dupes)

        geo.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    print("✅ Done! CSV + GeoJSON created.")


if __name__ == "__main__":
    add_og_fields()
