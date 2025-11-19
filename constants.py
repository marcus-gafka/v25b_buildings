from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
CHECKLISTS_DIR = ROOT_DIR / "checklists"
FIELDWORK_DIR = ROOT_DIR / "fieldwork"

RAW_GEOJSON = DATA_DIR / "VPC_Buildings_Total_1.geojson"

FILTERED_GEOJSON = DATA_DIR / "VPC_Buildings_Filtered.geojson"
FILTERED_CSV = DATA_DIR / "VPC_Buildings_Filtered.csv"

ALIAS_GEOJSON = DATA_DIR / "VPC_Buildings_Total_With_Aliases.geojson"
ALIAS_CSV = DATA_DIR / "VPC_Buildings_Total_With_Aliases.csv"

WATER_CONSUMPTION_CSV = DATA_DIR / "VPC_Water_Consumption.csv"
FILTERED_WATER_CSV = DATA_DIR / "VPC_Water_Consumption_Filtered.csv"

ADDRESS_CSV = DATA_DIR / "VPC_Addresses_Total.csv"
FILTERED_ADDRESS_CSV = DATA_DIR / "VPC_Addresses_Filtered.csv"

TOTAL_GEOIDS_CSV = DATA_DIR / "VPC_Geoids.csv"
TOTAL_CHECKLIST_CSV = CHECKLISTS_DIR / "!TOTAL.csv"
TOTAL_ADDRESS_CSV = CHECKLISTS_DIR / "!TOTAL-A.csv"
TOTAL_FIELDWORK_CSV = FIELDWORK_DIR / "!TOTAL-F.csv"

LIN_REG_CSV = DATA_DIR / "LinReg_Models.csv"

BUILDING_FIELD = "TARGET_FID_12_13"         # unique buidling identifier
TRACT_FIELD = "SEZ21"                       # unique tract identifier
ISLAND_FIELD = "Codice"                     # unique island identifier
SESTIERE_FIELD = "Codice_Ses"               # unique sestiere identifier