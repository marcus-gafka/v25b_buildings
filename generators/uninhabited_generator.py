import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import DATA_DIR
import os
import pandas as pd


def find_missing_aliases():
    # File paths
    total_fp = os.path.join(DATA_DIR, "VPC_Buildings_Total_With_Aliases.csv")
    inhabited_fp = os.path.join(DATA_DIR, "VPC_Buildings_Inhabited_V1.csv")

    # Load CSVs
    total_df = pd.read_csv(total_fp, dtype=str)
    inhabited_df = pd.read_csv(inhabited_fp, dtype=str)

    # Ensure the key column exists
    if "full_alias" not in total_df.columns:
        raise ValueError("full_alias not found in VPC_Buildings_Total_With_Aliases.csv")

    if "full_alias" not in inhabited_df.columns:
        raise ValueError("full_alias not found in VPC_Buildings_Inhabited_V1.csv")

    # Convert to sets for comparison
    total_aliases = set(total_df["full_alias"].dropna().unique())
    inhabited_aliases = set(inhabited_df["full_alias"].dropna().unique())

    # Find aliases only in total
    only_in_total = sorted(total_aliases - inhabited_aliases)

    print(f"🔎 Found {len(only_in_total)} aliases only in total:")
    for alias in only_in_total:
        print(alias)

    # Optional: save to CSV
    out_path = os.path.join(DATA_DIR, "VPC_Buildings_Uninhabited_V1.csv")
    pd.DataFrame({"full_alias": only_in_total}).to_csv(out_path, index=False)
    print(f"\n💾 Saved to {out_path}")

if __name__ == "__main__":
    find_missing_aliases()
