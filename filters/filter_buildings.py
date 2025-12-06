import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from constants import RAW_GEOJSON, FILTERED_CSV, BUILDING_FIELD, ISLAND_FIELD
import json
import pandas as pd

KEEP_FIELDS = [
    "Qu_Terra",
    "Tipologia",
    "Qu_Gronda",
    "SEZ21",
    "POP21",
    "ABI21",
    "FAM21",
    "EDI21",
    "TP_CLS_ED",
    "Superficie",
    "TipoFun",
    "SpecFun",
    "Dest_Pt_An",
    BUILDING_FIELD,   # building alias
    ISLAND_FIELD      # Codice
]

def main():
    print("📂 Loading raw GeoJSON...")
    with open(RAW_GEOJSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    print("🧹 Filtering features...")
    for feature in data["features"]:
        props = feature.get("properties", {})
        new_props = {k: props.get(k, None) for k in KEEP_FIELDS}
        new_props["geometry"] = feature.get("geometry")  # optional
        rows.append(new_props)

    print("💾 Converting to DataFrame...")
    df = pd.DataFrame(rows)

    # Put BUILDING_FIELD first
    columns = [BUILDING_FIELD] + [c for c in df.columns if c != BUILDING_FIELD]
    df = df[columns]

    print(f"💾 Saving CSV → {FILTERED_CSV}")
    df.to_csv(FILTERED_CSV, index=False)

    print("✅ Done — CSV created with filtered fields only.")

if __name__ == "__main__":
    main()
