from dataset import Dataset
from file_utils import geojson_to_csv
from constants import RAW_GEOJSON, FILTERED_GEOJSON, FILTERED_CSV, BUILDING_FIELD
import pandas as pd
from copy import deepcopy
import json

KEEP_FIELDS = [
    "CodLiv",               #
    "Qu_Terra",             # 
    "Superficie",           # 
    "Tipologia",            # 
    "Dest_Pt_An",           # 
    "Dest_Ps_An",           # 
    "Vinc_Mon",             # 
    "Cod_Sest",             # 
    "TipoFun",              # 
    "SpecFun",              # 
    "Qu_Gronda",            # 
    "Xc",                   # 
    "Yc",                   # 
    "Perimetro",            # 
    "CivicNumber",          # 
    "SEZ21",                # 
    "SEZ21_ID",             # 
    "COD_TIPO_S",           # 
    "COD_ZIC",              # 
    "COD_ACQUE",            # 
    "COD_ISOLE",            # 
    "COD_AREA_S",           # 
    "COM_ASC1",             # 
    "COM_ASC2",             # 
    "COM_ASC3",             # 
    "POP21",                # 
    "FAM21",                # 
    "ABI21",                # 
    "EDI21",                # 
    "SHAPE_Leng",           # 
    "Shape__Area_1",        # 
    "Shape__Length_1",      # 
    "ID",                   # 
    "Nome_Sesti",           # 
    "Codice_Ses",           # 
    "FOGLIO_NEW",           # 
    "ALLEGATO",             # 
    "MAPPALE",              # 
    "CXF",                  # 
    "Shape__Area_12",       # 
    "Shape__Length_12",     # 
    "Numero",               # 
    "Codice",               # 
    "Nome_Isola",           # 
    "Superficie_1",         # 
    "Codice_Ses_1",         # 
    "Insula_Num",           # 
    "Perimetro_1",          # 
    "PROG",                 # 
    "TP_CLS_ED",            # 
    "DESC_TIPO",            # 
    "DS_AGGREG",            # 
    "NTA",                  # 
    "STATO_ALT",            # 
    "DATA_CSC",             # 
    "GEOURBA_Cl",           #
    BUILDING_FIELD,     # 
]

# REMOVED FIELDS:
"""
"COD_ISAM",             # 
"COD_MONT_D",           # 
"COD_REG",              # 
"COD_UTS",              # 
"COMUNE",               # 
"FOGLIO_OLD",           # 
"Join_Count",           # 
"Join_Count_1",         # 
"Join_Count_12",        # 
"Join_Count_12_13",     # 
"LOC21_ID",             # 
"NoBar",                # 
"NOTE",                 # 
"NOTENONVIS",           # 
"Notes",                # 
"OBJECTID",             # 
"OBJECTID_1",           # 
"OBJECTID_12",          # 
"PRO_COM",              # 
"RecordDate",           # 
"RICOND_TP",            # 
"SCHEDA",               # 
"SEZ_TXT",              # 
"Sez_Cen91",            # 
"SIST_RIF_O",           # 
"SVILUPPO",             # 
"TARGET_FID",           # 
"TARGET_FID_1",         # 
"TARGET_FID_12",        # 
"""

def filter_fields(dataset: Dataset, keep_fields: list) -> Dataset:
    """
    Return a new Dataset containing only the properties listed in keep_fields.
    """
    filtered_features = []
    for feature in dataset.features:
        props = feature.get("properties", {})
        new_props = {k: props.get(k, None) for k in keep_fields if k in props or k == BUILDING_FIELD}
        filtered_feature = {
            "type": feature.get("type", "Feature"),
            "properties": new_props,
            "geometry": feature.get("geometry")
        }
        filtered_features.append(filtered_feature)

    # Create a new Dataset object with filtered features
    filtered_dataset = deepcopy(dataset)
    filtered_dataset.features = filtered_features
    return filtered_dataset

def main():
    print("📂 Loading raw GeoJSON...")
    dataset = Dataset(RAW_GEOJSON)

    print("🧹 Filtering fields...")
    filtered_dataset = filter_fields(dataset, KEEP_FIELDS)

    # --- Save filtered GeoJSON properly ---
    print("💾 Saving filtered GeoJSON...")
    geojson_dict = {
        "type": "FeatureCollection",
        "features": filtered_dataset.features
    }
    with open(FILTERED_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson_dict, f, ensure_ascii=False, indent=2)

    # --- Save CSV with BUILDING_FIELD first ---
    print("💾 Saving CSV with BUILDING_FIELD first...")
    rows = []
    for f in filtered_dataset.features:
        props = f.get("properties", {}).copy()
        props["geometry"] = f.get("geometry")
        rows.append(props)

    df = pd.DataFrame(rows)
    columns = [BUILDING_FIELD] + [c for c in df.columns if c != BUILDING_FIELD]
    df = df[columns]
    df.to_csv(FILTERED_CSV, index=False)
    print(f"💾 CSV saved to {FILTERED_CSV}")
    print("✅ Filtering complete.")


if __name__ == "__main__":
    main()
