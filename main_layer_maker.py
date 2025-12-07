from dataset import Dataset
from constants import ALIAS_GEOJSON, ESTIMATES_DIR, ALIAS_CSV, ESTIMATES_CSV
import matplotlib.pyplot as plt

from estimation_null import estimation_null
from estimation_v0 import estimation_v0
from estimation_v1 import estimation_v1
from estimation_v2 import estimation_v2
from estimation_v3 import estimation_v3
from estimation_v4 import estimation_v4

import pandas as pd
import geopandas as gpd
from shapely import wkt

from file_utils import csv_to_geojson

def main():

    ds = Dataset(str(ALIAS_GEOJSON))
    #estimation_v4(ds,{"GERE"},False)
    estimation_v4(ds,{})
    ds.export_hierarchy_text(ESTIMATES_DIR / "Venice_hierarchy.txt")
    csv_to_geojson(ESTIMATES_DIR / "VPC_Estimates_V4.csv")

def add_og_fields():

    OUTPUT_CSV = "final/merged_output.csv"
    OUTPUT_GEOJSON = "final/merged_output.geojson"

    RENAME_COLUMNS = {
        # ---- RENAMED SHARED KEYS ----
        "bldg_id": "",
        "aliases_id": "",
        "alias_short": "",
        "alias_full": "",

        # ---- UNITS (ALIAS CSV) FIELDS ----
        "Nome_Sesti": "",
        "Codice": "",
        "CodLiv": "",
        "Qu_Terra": "",
        "Superficie": "",
        "Tipologia": "",
        "Dest_Pt_An": "",
        "Dest_Ps_An": "",
        "Vinc_Mon": "",
        "Cod_Sest": "",
        "TipoFun": "",
        "SpecFun": "",
        "Qu_Gronda": "",
        "Xc": "",
        "Yc": "",
        "Perimetro": "",
        "CivicNumber": "",
        "SEZ21": "",
        "SEZ21_ID": "",
        "COD_TIPO_S": "",
        "COD_ZIC": "",
        "COD_ACQUE": "",
        "COD_ISOLE": "",
        "COD_AREA_S": "",
        "COM_ASC1": "",
        "COM_ASC2": "",
        "COM_ASC3": "",
        "POP21": "",
        "FAM21": "",
        "ABI21": "",
        "EDI21": "",
        "SHAPE_Leng": "",
        "Shape__Area_1": "",
        "Shape__Length_1": "",
        "ID": "",
        "Codice_Ses": "",
        "FOGLIO_NEW": "",
        "ALLEGATO": "",
        "MAPPALE": "",
        "CXF": "",
        "Shape__Area_12": "",
        "Shape__Length_12": "",
        "Numero": "",
        "Nome_Isola": "",
        "Superficie_1": "",
        "Codice_Ses_1": "",
        "Insula_Num": "",
        "Perimetro_1": "",
        "PROG": "",
        "TP_CLS_ED": "",
        "DESC_TIPO": "",
        "DS_AGGREG": "",
        "NTA": "",
        "STATO_ALT": "",
        "DATA_CSC": "",
        "GEOURBA_Cl": "",

        # ---- ARCH CSV FIELDS ----
        "type": "",
        "height": "",
        "norm_height": "",
        "superficie": "",
        "norm_superficie": "",
        "floors_est": "",
        "units_est_meters": "",
        "units_est_volume": "",
        "units_est_merged": "",
        "pop_est": "",
        "full_nr": "",
        "units_res_primary": "",
        "units_res_empty": "",
        "units_res": "",
        "units_nr_secondary": "",
        "units_nr_empty": "",
        "units_nr_secondary_str": "",
        "units_nr_secondary_students": "",
        "units_nr": "",
        "res_pct": "",
        "nr_pct": "",
        "empty_pct": "",
        "res_adj_height": "",
        "nr_adj_height": "",
        "empty_adj_height": "",
        "measured": "",
        "surveyed": "",
        "geometry": "",
    }

    COLUMN_ORDER = {}

    print("📥 Loading CSVs...")
    esti = pd.read_csv(ESTIMATES_CSV)   # this CSV has building_id
    aliases = pd.read_csv(ALIAS_CSV)       # this CSV has TARGET_FID_12_13

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
        # keep only columns that actually exist
        final_cols = [c for c in COLUMN_ORDER if c in merged.columns]

        # append any extras not listed
        extras = [c for c in merged.columns if c not in final_cols]

        merged = merged[final_cols + extras]

    # ------------------------------
    # SAVE CSV
    # ------------------------------
    print("💾 Writing CSV output...")
    merged.to_csv(OUTPUT_CSV, index=False)

    # ------------------------------
    # GEOJSON EXPORT
    # ------------------------------

    print("🌍 Converting geometry (WKT → GeoDataFrame)...")

    # Convert WKT to shapely geometries
    merged["geometry"] = merged["geometry"].apply(wkt.loads)

    geo = gpd.GeoDataFrame(
        merged,
        geometry="geometry",
        crs="EPSG:4326"
    )

    print("💾 Writing GeoJSON...")
    geo.to_file(OUTPUT_GEOJSON, driver="GeoJSON")

    print("✅ Done! CSV + GeoJSON created.")

if __name__ == "__main__":
    main()
    #add_og_fields()