import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from constants import TOTAL_HOTEL_CSV, TOTAL_STR_CSV, DATA_DIR, HOTELS_STRS_DIR

def combine_csvs(keyword: str, output_file: Path):
    print(f"📂 Combining CSVs with '{keyword}' in {HOTELS_STRS_DIR}...")
    all_files = list(HOTELS_STRS_DIR.glob("*.csv"))
    matched_files = [f for f in all_files if keyword.lower() in f.name.lower()]
    if not matched_files:
        print(f"⚠️ No CSV files found containing '{keyword}'")
        return
    
    df_list = []
    for f in matched_files:
        print(f"  Reading {f.name}...")
        df_list.append(pd.read_csv(f))
    
    combined_df = pd.concat(df_list, ignore_index=True)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(output_file, index=False)
    print(f"✅ Combined {len(matched_files)} files into {output_file}")

def main():
    combine_csvs("hotels", TOTAL_HOTEL_CSV)
    combine_csvs("str", TOTAL_STR_CSV)

if __name__ == "__main__":
    main()
