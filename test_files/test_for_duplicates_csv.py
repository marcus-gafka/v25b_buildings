import pandas as pd

# === CONFIG ===
CSV_PATH = "data/VPC_Water_Consumption.csv"
FIELD = "FID"

# === LOAD CSV ===
print(f"📂 Loading {CSV_PATH}...")
df = pd.read_csv(CSV_PATH)
print(f"✅ Loaded {len(df)} rows.")

# === CHECK FOR DUPLICATES ===
if FIELD not in df.columns:
    print(f"❌ Field '{FIELD}' not found in CSV columns:")
    print(df.columns)
else:
    duplicates = df[df.duplicated(subset=FIELD, keep=False)]
    count = len(duplicates)

    if count == 0:
        print(f"✅ No duplicates found in field '{FIELD}'.")
    else:
        print(f"⚠️ Found {count} duplicates in field '{FIELD}':")
        print(duplicates[[FIELD]].value_counts().head(10))
