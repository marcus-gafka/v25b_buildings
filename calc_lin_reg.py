import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import re
from constants import FIELDWORK_DIR, TOTAL_FIELDWORK_CSV, LIN_REG_CSV
import matplotlib.pyplot as plt

# === LOAD ALL FIELDWORK FILES ===
def load_fieldwork_files():
    """Load all XX-XXXX-F.csv files except !TOTAL-F.csv."""
    dfs = []
    for file in FIELDWORK_DIR.glob("*-F.csv"):
        if file.name.startswith("!"):
            continue
        if re.match(r"^[A-Z]{2}-[A-Z0-9]{3,}-F\.csv$", file.name, re.IGNORECASE):
            df = pd.read_csv(file)
            df["source_file"] = file.name
            dfs.append(df)
    return dfs

# === REBUILD TOTAL FIELDWORK CSV ===
def rebuild_total_fieldwork_csv(dfs):
    """Rebuild !TOTAL-F.csv from all fieldwork CSVs."""
    columns = ["short_alias", "TP_CLS_ED", "Qu_Gronda", "Qu_Terra", "Superficie", "Measured Height", "Floors"]
    total_df = pd.DataFrame(columns=columns)

    for df in dfs:
        df = df[columns]
        total_df = pd.concat([total_df, df], ignore_index=True)

    total_df.to_csv(TOTAL_FIELDWORK_CSV, sep=",", index=False)
    return total_df

# === CLEAN DATA ===
def clean_data(df):
    """Convert numeric columns and clean invalid Qu_Gronda values."""
    df = df.copy()
    for col in ["Qu_Gronda", "Qu_Terra", "Measured Height", "Floors"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.loc[df["Qu_Gronda"].isin([0, 9999]), "Qu_Gronda"] = np.nan
    return df

# === TRAIN LINEAR MODELS ON ΔQu VS Floors ===
def train_linear_models(df):
    results = []

    for tp_class, group in df.groupby("TP_CLS_ED"):
        entry = {
            "TP_CLS_ED": tp_class,
            "m_qu": np.nan,
            "b_qu": np.nan,
            "r2_qu": np.nan,
            "1/m_qu": np.nan,
            "blank": "",
            "qu_count": 0,
            "m_f": np.nan,
            "b_f": np.nan,
            "r2_f": np.nan,
            "1/m_f": np.nan,
            "f_count": 0
        }

        # --- ΔQu = Qu_Gronda - Qu_Terra vs Floors ---
        qu_data = group.dropna(subset=["Qu_Gronda", "Qu_Terra", "Floors"])
        qu_data = qu_data[(qu_data["Qu_Gronda"] != 0) & (qu_data["Qu_Gronda"] != 9999)]  # filter invalid
        entry["qu_count"] = len(qu_data)
        if len(qu_data) >= 2:
            qu_data["Delta_Qu"] = qu_data["Qu_Gronda"] - qu_data["Qu_Terra"]
            X_qu = qu_data[["Delta_Qu"]].values
            y_qu = qu_data["Floors"].values
            model_qu = LinearRegression().fit(X_qu, y_qu)
            entry["m_qu"] = float(model_qu.coef_[0])
            entry["b_qu"] = float(model_qu.intercept_)
            entry["r2_qu"] = float(model_qu.score(X_qu, y_qu))
            if entry["m_qu"] != 0:
                entry["1/m_qu"] = 1 / entry["m_qu"]

        # --- Measured Height vs Floors ---
        f_data = group.dropna(subset=["Measured Height", "Floors"])
        entry["f_count"] = len(f_data)
        if len(f_data) >= 2:
            X_f = f_data[["Measured Height"]].values
            y_f = f_data["Floors"].values
            model_f = LinearRegression().fit(X_f, y_f)
            entry["m_f"] = float(model_f.coef_[0])
            entry["b_f"] = float(model_f.intercept_)
            entry["r2_f"] = float(model_f.score(X_f, y_f))
            if entry["m_f"] != 0:
                entry["1/m_f"] = 1 / entry["m_f"]

        results.append(entry)

    result_df = pd.DataFrame(results)

    numeric_cols = ["m_qu", "b_qu", "r2_qu", "1/m_qu", "m_f", "b_f", "r2_f", "1/m_f"]
    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = result_df[col].round(3)

    return result_df

# === PLOTTING ΔQu VS Floors SIDE-BY-SIDE ===
def plot_regression_side_by_side(df):
    colors = plt.cm.tab10.colors
    tp_types = sorted(df["TP_CLS_ED"].dropna().unique())

    fig, axes = plt.subplots(1, 2, figsize=(16,6))
    ax_qu, ax_f = axes

    # --- ΔQu vs Floors ---
    for i, tp_class in enumerate(tp_types):
        group = df[df["TP_CLS_ED"] == tp_class].dropna(subset=["Qu_Gronda", "Qu_Terra", "Floors"])
        group = group[(group["Qu_Gronda"] != 0) & (group["Qu_Gronda"] != 9999)]
        if len(group) == 0:
            continue
        group["Delta_Qu"] = group["Qu_Gronda"] - group["Qu_Terra"]
        ax_qu.scatter(group["Delta_Qu"], group["Floors"], color=colors[i%10], label=f"{tp_class} points")
        if len(group) >= 2:
            X = group[["Delta_Qu"]].values
            y = group["Floors"].values
            model = LinearRegression().fit(X, y)
            x_range = np.linspace(np.nanmin(X), np.nanmax(X), 100)
            y_pred = model.predict(x_range.reshape(-1,1))
            ax_qu.plot(x_range, y_pred, color=colors[i%10], linestyle="--", label=f"{tp_class} fit")

    ax_qu.set_xlabel("Qu_Gronda - Qu_Terra")
    ax_qu.set_ylabel("Floors")
    ax_qu.set_title("Floors vs ΔQu by TP_CLS_ED")
    ax_qu.legend()

    # --- Measured Height vs Floors (same as before) ---
    for i, tp_class in enumerate(tp_types):
        group = df[df["TP_CLS_ED"] == tp_class].dropna(subset=["Measured Height", "Floors"])
        ax_f.scatter(group["Measured Height"], group["Floors"], color=colors[i%10], label=f"{tp_class} points")
        if len(group) >= 2:
            X = group[["Measured Height"]].values
            y = group["Floors"].values
            model = LinearRegression().fit(X, y)
            x_range = np.linspace(np.nanmin(X), np.nanmax(X), 100)
            y_pred = model.predict(x_range.reshape(-1,1))
            ax_f.plot(x_range, y_pred, color=colors[i%10], linestyle="--", label=f"{tp_class} fit")

    ax_f.set_xlabel("Measured Height")
    ax_f.set_ylabel("Floors")
    ax_f.set_title("Floors vs Measured Height by TP_CLS_ED")
    ax_f.legend()

    plt.tight_layout()
    plt.show()

# === MAIN SCRIPT ===
if __name__ == "__main__":
    print("📂 Loading fieldwork CSVs...")
    dfs = load_fieldwork_files()
    print(f"✅ Loaded {len(dfs)} fieldwork files")

    print("🔄 Rebuilding !TOTAL-F.csv...")
    total_df = rebuild_total_fieldwork_csv(dfs)
    print(f"✅ !TOTAL-F.csv rebuilt with {len(total_df)} rows.")

    print("🧹 Cleaning data...")
    clean_df = clean_data(total_df)

    print("📈 Training split linear regression models...")
    models_df = train_linear_models(clean_df)

    total_row = {
        "TP_CLS_ED": "Total:",
        "m_qu": "",
        "b_qu": "",
        "r2_qu": "",
        "1/m_qu": "",
        "blank": "",
        "qu_count": f"=SUM(G2:G{len(models_df)+1})",  # Excel formula for column G
        "m_f": "",
        "b_f": "",
        "r2_f": "",
        "1/m_f": "",
        "f_count": f"=SUM(L2:L{len(models_df)+1})"   # Excel formula for column L
    }

    models_df = pd.concat([models_df, pd.DataFrame([total_row])], ignore_index=True)

    ## COMMENT OUT THIS LINE TO SKIP OVERWRITING LIN_REG_MODELS ---------------------------------------------------

    models_df.to_csv(LIN_REG_CSV, index=False)

    ## ------------------------------------------------------------------------------------------------------------

    print(f"✅ Models saved to {LIN_REG_CSV}")

    print("📊 Plotting regression results...")
    plot_regression_side_by_side(clean_df)
