import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from constants import WATER_CONSUMPTION_CSV, FILTERED_WATER_CSV

# Columns to keep
KEEP_COLS = [
    "EANL_Tipo_impianto",
    "Cat_Tariffa",
    "Nuclei_domestici",
    "Nuclei_commerciali",
    "Nuclei_non_residenti",
    "Condominio",
    "Componenti",
    "Località",
    "ProccessedVia",
    "ProcessedAddress",
    "Consumo_medio_2020",
    "Consumo_medio_2021",
    "Consumo_medio_2022",
    "Consumo_medio_2023",
    "Consumo_medio_2024"
]

# Load CSV
df = pd.read_csv(WATER_CONSUMPTION_CSV)

# Filter for Località = VENEZIA
df_filtered = df[df["Località"].str.upper() == "VENEZIA"]

# Keep only the requested columns
df_filtered = df_filtered[KEEP_COLS]

# Save to new CSV
df_filtered.to_csv(FILTERED_WATER_CSV, index=False)
print(f"✅ Filtered CSV saved to {FILTERED_WATER_CSV}")
