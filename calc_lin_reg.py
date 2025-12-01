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
    columns = [
        "short_alias",
        "TP_CLS_ED",
        "Qu_Gronda",
        "Qu_Terra",
        "Superficie",
        "Measured Height",
        "Floors"
    ]
    total_df = pd.concat([df[columns] for df in dfs], ignore_index=True)
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

    valid_for_tp = df.dropna(subset=["TP_CLS_ED"])
    valid_qu_misc = valid_for_tp.dropna(subset=["Qu_Gronda", "Qu_Terra", "Floors"])
    valid_qu_misc = valid_qu_misc[(valid_qu_misc["Qu_Gronda"] != 0) &
                                  (valid_qu_misc["Qu_Gronda"] != 9999)]

    valid_f_misc = valid_for_tp.dropna(subset=["Measured Height", "Floors"])

    # === TP-SPECIFIC MODELS ===
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

        # ΔQu model
        qu_data = group.dropna(subset=["Qu_Gronda", "Qu_Terra", "Floors"])
        qu_data = qu_data[(qu_data["Qu_Gronda"] != 0) & (qu_data["Qu_Gronda"] != 9999)]
        entry["qu_count"] = len(qu_data)

        if len(qu_data) >= 2:
            qu_data = qu_data.copy()
            qu_data["Delta_Qu"] = qu_data["Qu_Gronda"] - qu_data["Qu_Terra"]
            X_qu = qu_data[["Delta_Qu"]].values
            y_qu = qu_data["Floors"].values
            model_qu = LinearRegression().fit(X_qu, y_qu)
            entry["m_qu"] = float(model_qu.coef_[0])
            entry["b_qu"] = float(model_qu.intercept_)
            entry["r2_qu"] = float(model_qu.score(X_qu, y_qu))
            if entry["m_qu"] != 0:
                entry["1/m_qu"] = 1 / entry["m_qu"]

        # Measured Height model
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

    # === GLOBAL "MISC" MODEL ===
    misc_entry = {"TP_CLS_ED": "misc", "blank": ""}

    if len(valid_qu_misc) >= 2:
        valid_qu_misc = valid_qu_misc.copy()
        valid_qu_misc["Delta_Qu"] = valid_qu_misc["Qu_Gronda"] - valid_qu_misc["Qu_Terra"]
        X_qu = valid_qu_misc[["Delta_Qu"]].values
        y_qu = valid_qu_misc["Floors"].values
        model_qu = LinearRegression().fit(X_qu, y_qu)
        misc_entry["m_qu"] = float(model_qu.coef_[0])
        misc_entry["b_qu"] = float(model_qu.intercept_)
        misc_entry["r2_qu"] = float(model_qu.score(X_qu, y_qu))
        misc_entry["1/m_qu"] = 1 / misc_entry["m_qu"]
        misc_entry["qu_count"] = len(valid_qu_misc)
    else:
        misc_entry["m_qu"] = misc_entry["b_qu"] = misc_entry["r2_qu"] = misc_entry["1/m_qu"] = np.nan
        misc_entry["qu_count"] = 0

    if len(valid_f_misc) >= 2:
        X_f = valid_f_misc[["Measured Height"]].values
        y_f = valid_f_misc["Floors"].values
        model_f = LinearRegression().fit(X_f, y_f)
        misc_entry["m_f"] = float(model_f.coef_[0])
        misc_entry["b_f"] = float(model_f.intercept_)
        misc_entry["r2_f"] = float(model_f.score(X_f, y_f))
        misc_entry["1/m_f"] = 1 / misc_entry["m_f"]
        misc_entry["f_count"] = len(valid_f_misc)
    else:
        misc_entry["m_f"] = misc_entry["b_f"] = misc_entry["r2_f"] = misc_entry["1/m_f"] = np.nan
        misc_entry["f_count"] = 0

    result_df = pd.concat([result_df, pd.DataFrame([misc_entry])], ignore_index=True)

    numeric_cols = ["m_qu", "b_qu", "r2_qu", "1/m_qu", "m_f", "b_f", "r2_f", "1/m_f"]
    for col in numeric_cols:
        result_df[col] = result_df[col].astype(float).round(3)

    return result_df

# === PLOTTING ΔQu VS Floors SIDE-BY-SIDE ===
def plot_regression_side_by_side(df):
    colors = plt.cm.tab10.colors
    tp_types = sorted(df["TP_CLS_ED"].dropna().unique())

    fig, axes = plt.subplots(1, 2, figsize=(16,6))
    ax_qu, ax_f = axes

    # --- ΔQu vs Floors ---
    for i, tp_class in enumerate(tp_types):
        group = df[df["TP_CLS_ED"] == tp_class].dropna(subset=["Qu_Gronda", "Qu_Terra", "Floors"]).copy()
        group = group[(group["Qu_Gronda"] != 0) & (group["Qu_Gronda"] != 9999)]
        if len(group) == 0:
            continue

        group["Delta_Qu"] = group["Qu_Gronda"] - group["Qu_Terra"]

        # POINTS — visible in legend
        ax_qu.scatter(
            group["Delta_Qu"],
            group["Floors"],
            color=colors[i % 10],
            label=f"{tp_class}"
        )

        if len(group) >= 2:
            X = group[["Delta_Qu"]].values
            y = group["Floors"].values
            model = LinearRegression().fit(X, y)
            x_range = np.linspace(0, 30, 100)
            y_pred = model.predict(x_range.reshape(-1, 1))

            # LINES — NO LEGEND ENTRY
            ax_qu.plot(
                x_range,
                y_pred,
                color=colors[i % 10],
                linestyle="--",
                label="_nolegend_"
            )

    ax_qu.set_xlabel("Qu_Gronda - Qu_Terra")
    ax_qu.set_ylabel("Floors")
    ax_qu.set_title("Floors vs ΔQu by TP_CLS_ED")
    ax_qu.set_xlim(0, 30)
    ax_qu.set_ylim(0, 8)
    ax_qu.legend()

    # --- Measured Height vs Floors ---
    for i, tp_class in enumerate(tp_types):
        group = df[df["TP_CLS_ED"] == tp_class].dropna(subset=["Measured Height", "Floors"]).copy()
        if len(group) == 0:
            continue

        # POINTS — visible in legend
        ax_f.scatter(
            group["Measured Height"],
            group["Floors"],
            color=colors[i % 10],
            label=f"{tp_class}"
        )

        if len(group) >= 2:
            X = group[["Measured Height"]].values
            y = group["Floors"].values
            model = LinearRegression().fit(X, y)
            x_range = np.linspace(0, 30, 100)
            y_pred = model.predict(x_range.reshape(-1, 1))

            # LINES — NO LEGEND ENTRY
            ax_f.plot(
                x_range,
                y_pred,
                color=colors[i % 10],
                linestyle="--",
                label="_nolegend_"
            )

    ax_f.set_xlabel("Measured Height")
    ax_f.set_ylabel("Floors")
    ax_f.set_title("Floors vs Measured Height by TP_CLS_ED")
    ax_f.set_xlim(0, 30)
    ax_f.set_ylim(0, 8)
    ax_f.legend()

    plt.tight_layout()
    plt.show()

# === MAIN SCRIPT ===
if __name__ == "__main__":
    dfs = load_fieldwork_files()
    total_df = rebuild_total_fieldwork_csv(dfs)
    clean_df = clean_data(total_df)
    models_df = train_linear_models(clean_df)

    models_df.to_csv(LIN_REG_CSV, index=False)
    plot_regression_side_by_side(clean_df)

    print("✅ Saved regression models to:", LIN_REG_CSV)
