import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from constants import (
    TOTAL_HOTEL_CSV, TOTAL_HOTELS_EXTRA_CSV, TOTAL_STR_CSV,
    FILTERED_HOTEL_CSV, FILTERED_HOTELS_EXTRA_CSV, FILTERED_STR_CSV
)

# -----------------------------
# COLUMN SETS (you fill these)
# -----------------------------
KEEP_HOTEL_COLS = [
    "FID",
    "INDIRIZZO",
    "DENOMINAZI"
]

KEEP_HOTELS_EXTRA_COLS = [
    "FID",
    "INDIRIZZO",
    "DENOMINAZI"
]

KEEP_STR_COLS = [
    "FID",
    "INDIRIZZO",
    "Name"
]

# -----------------------------
# Venice abbreviation map
# -----------------------------
SESTIERE_MAP = {
    "SAN MARCO": "SM",
    "SAN POLO": "SP",
    "CASTELLO": "CA",
    "CANNAREGIO": "CN",
    "DORSODURO": "DD",
    "SANTA CROCE": "SC",
    "GIUDECCA (VENEZIA)": "GD"
}

# -----------------------------
# Convert INDIRIZZO → ADDRESS
# -----------------------------
def convert_indirizzo(ind):
    if pd.isna(ind):
        return None

    parts = [p.strip() for p in ind.split(",")]

    # malformed address
    if len(parts) != 2:
        cleaned = ind.replace(",", "").replace("/", "").replace(" ", "")
        return f"X_{cleaned}"

    place, number = parts
    place_upper = place.upper()
    number_clean = number.replace("/", "").replace(" ", "")

    if place_upper in SESTIERE_MAP:
        return f"{SESTIERE_MAP[place_upper]}{number_clean}"
    else:
        # address not inside Venice sestieri
        return f"X_{place_upper}{number_clean}"


# -----------------------------
# Filter + add ADDRESS + sort by FID
# -----------------------------
def filter_csv(input_csv, output_csv, keep_cols):
    print(f"📂 Loading {input_csv} ...")
    df = pd.read_csv(input_csv)

    # Keep only wanted columns
    if keep_cols:
        missing = set(keep_cols) - set(df.columns)
        if missing:
            raise ValueError(f"❌ Missing columns in {input_csv}: {missing}")
        df = df[keep_cols]

    # Add generated address column (if INDIRIZZO exists)
    if "INDIRIZZO" in df.columns:
        df["ADDRESS"] = df["INDIRIZZO"].apply(convert_indirizzo)
    else:
        print("⚠️  No INDIRIZZO column found — ADDRESS field skipped.")

    # Sort by FID if present
    if "FID" in df.columns:
        df = df.sort_values(by="FID", ascending=True)
    else:
        print("⚠️  No FID column found — skipping sorting.")

    # Save output
    df.to_csv(output_csv, index=False)
    print(f"✅ Saved filtered file → {output_csv}\n")


def main():
    print("🔎 Filtering datasets...\n")

    filter_csv(TOTAL_HOTEL_CSV, FILTERED_HOTEL_CSV, KEEP_HOTEL_COLS)
    filter_csv(TOTAL_HOTELS_EXTRA_CSV, FILTERED_HOTELS_EXTRA_CSV, KEEP_HOTELS_EXTRA_COLS)
    filter_csv(TOTAL_STR_CSV, FILTERED_STR_CSV, KEEP_STR_COLS)

    print("🎉 All filtered datasets saved!")


if __name__ == "__main__":
    main()
