import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import FILTERED_WATER_CSV

import pandas as pd
from pathlib import Path

# Load the filtered water CSV
df = pd.read_csv(FILTERED_WATER_CSV)

# Standardize ProcessedAddress for matching
df["ProcessedAddress"] = df["ProcessedAddress"].astype(str).str.strip().str.upper()

# Count water meters per address
meters_per_address = df.groupby("ProcessedAddress")["EANL_Tipo_impianto"].count().reset_index()
meters_per_address.rename(columns={"EANL_Tipo_impianto": "NumMeters"}, inplace=True)

# Output CSV to current directory
output_path = Path("meters_per_address.csv")
meters_per_address.to_csv(output_path, index=False)

print(f"✅ Water meter counts per address saved to {output_path}")
print(meters_per_address)
