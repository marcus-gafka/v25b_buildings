from pathlib import Path

# Base data directory (relative to this file)
ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"

# Common file paths
RAW_GEOJSON = DATA_DIR / "VPC_Buildings_Total_1.geojson"
FILTERED_GEOJSON = DATA_DIR / "VPC_Buildings_Filtered.geojson"
FILTERED_CSV = DATA_DIR / "VPC_Buildings_Filtered.csv"
ALIAS_GEOJSON = DATA_DIR / "VPC_Buildings_With_Aliases.geojson"
ALIAS_CSV = DATA_DIR / "VPC_Buildings_With_Aliases.csv"

# Common column names
BUILDING_FIELD = "TARGET_FID_12_13"         # unique buidling identifier
TRACT_FIELD = "SEZ21"                       # unique tract identifier
ISLAND_FIELD = "Codice"                     # unique island identifier
SESTIERE_FIELD = "Codice_Ses"               # unique sestiere identifier