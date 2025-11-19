import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from constants import ALIAS_CSV, DATA_DIR

def filter_alias_csv():
    print(f"📂 Loading: {ALIAS_CSV}")

    df = pd.read_csv(ALIAS_CSV)

    # Correct field names
    id_col = "TARGET_FID_12_13"
    keep_cols = [id_col, "full_alias", "short_alias"]

    # Check for missing columns
    missing = [c for c in keep_cols if c not in df.columns]
    if missing:
        print(f"⚠️ Warning: Missing columns in CSV: {missing}")

    # Keep only columns that exist
    existing_cols = [c for c in keep_cols if c in df.columns]
    filtered = df[existing_cols].copy()

    # --- Force ID column to int and sort ---
    if id_col in filtered.columns:
        filtered[id_col] = (
            pd.to_numeric(filtered[id_col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

        filtered = filtered.sort_values(id_col)

    # --- Reorder columns ---
    ordered_cols = [id_col, "full_alias", "short_alias"]
    filtered = filtered[[c for c in ordered_cols if c in filtered.columns]]

    # Output path
    out_path = DATA_DIR / "VPC_Alias_Merge.csv"
    print(f"💾 Saving filtered CSV to {out_path}")

    filtered.to_csv(out_path, index=False)

    print("✅ Done.")

if __name__ == "__main__":
    filter_alias_csv()
