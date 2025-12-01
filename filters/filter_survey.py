import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from constants import SURVEY_CSV, FILTERED_SURVEY_CSV

KEEP_FIELDS = [
    "Number of Doorbells",
    "Number of Floors",
    "Additional Notes",
    "Building Alias",
    "Island Code",
    "Floor 0",
    "Floor 1",
    "Floor 2",
    "Floor 3",
    "Floor 4",
    "Floor 5",
    "Floor 6",
    "Floor 7"
]

def main():
    print("📂 Loading survey CSV...")
    df = pd.read_csv(SURVEY_CSV, dtype=str)

    print("🧹 Filtering fields...")
    df_filtered = df[[c for c in KEEP_FIELDS if c in df.columns]].copy()

    # --- Remove newlines in additional notes ---
    if "Additional Notes" in df_filtered.columns:
        print("🧽 Cleaning newline characters in Additional Notes...")
        df_filtered["Additional Notes"] = (
            df_filtered["Additional Notes"]
            .fillna("")
            .astype(str)
            .str.replace(r"[\r\n]+", " ", regex=True)
            .str.strip()
        )

    # --- Create short_alias ---
    print("🔧 Creating short_alias field...")

    df_filtered["Island Code"] = df_filtered["Island Code"].fillna("").str.upper().str[:4]
    df_filtered["Building Alias"] = (
        pd.to_numeric(df_filtered["Building Alias"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    df_filtered["short_alias"] = (
        df_filtered["Island Code"] + "-" +
        df_filtered["Building Alias"].astype(str).str.zfill(3)
    )

    # Drop original columns
    df_filtered = df_filtered.drop(columns=["Island Code", "Building Alias"])

    print("🔠 Sorting by short_alias...")
    df_filtered = df_filtered.sort_values("short_alias")

    cols = ["short_alias"] + [c for c in df_filtered.columns if c != "short_alias"]
    df_filtered = df_filtered[cols]

    print("💾 Saving filtered survey CSV...")
    df_filtered.to_csv(FILTERED_SURVEY_CSV, index=False)
    print(f"✅ CSV saved to {FILTERED_SURVEY_CSV}")

if __name__ == "__main__":
    main()
