import pandas as pd
from pathlib import Path
from constants import FILTERED_SURVEY_CSV, ESTIMATES_DIR
import matplotlib.pyplot as plt


def error_to_color(error, max_range):
    """
    Map an error value to a color: green (0) → yellow → red (max magnitude).
    """
    if max_range == 0:
        return (0.0, 0.7, 0.0)  # fallback green if no variation
    mag = min(abs(error) / max_range, 1)

    if mag < 0.5:
        # green → yellow
        ratio = mag / 0.5
        r = ratio
        g = 1.0
        b = 0.0
    else:
        # yellow → red
        ratio = (mag - 0.5) / 0.5
        r = 1.0
        g = 1.0 - ratio
        b = 0.0

    return (r, g, b)


def plot_error_distribution(errors, title, xlabel):
    """
    Plot a single error distribution with color mapping.
    """
    max_val = max(abs(errors.index).max(), 1)
    colors = [error_to_color(e, max_val) for e in errors.index]

    plt.figure(figsize=(8, 5))
    plt.bar(errors.index, errors.values, color=colors, edgecolor='black')
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Number of Buildings")
    plt.grid(axis='y', alpha=0.6)
    plt.tight_layout()
    plt.show()


def main():
    print("📂 Loading survey CSV…")
    survey_df = pd.read_csv(FILTERED_SURVEY_CSV)

    # Ensure numeric fields
    survey_df["Number of Floors"] = pd.to_numeric(
        survey_df["Number of Floors"], errors="coerce"
    ).fillna(0).astype(int)

    survey_df["Number of Doorbells"] = pd.to_numeric(
        survey_df["Number of Doorbells"], errors="coerce"
    ).fillna(0).astype(int)

    print("📂 Loading estimates CSV…")
    est_path = ESTIMATES_DIR / "VPC_Estimates_V4.csv"
    est_df = pd.read_csv(est_path)

    print("🔗 Merging datasets…")
    merged = survey_df.merge(est_df, on="short_alias", how="left")

    # ------------------------------------------
    # Compute all errors
    # ------------------------------------------
    merged["floor_error"] = merged["floors_est"] - merged["Number of Floors"]
    merged["units_error_meters"] = merged["units_est_meters"] - merged["Number of Doorbells"]
    merged["units_error_volume"] = merged["units_est_volume"] - merged["Number of Doorbells"]
    merged["units_error_merged"] = merged["units_est_merged"] - merged["Number of Doorbells"]

    # ------------------------------------------
    # Save combined verification CSV
    # ------------------------------------------
    out_path = ESTIMATES_DIR / "V25B_Floor_And_Units_Verification.csv"
    merged[[
        "short_alias",
        "Number of Floors",
        "floors_est",
        "floor_error",
        "Number of Doorbells",
        "units_est_meters",
        "units_error_meters",
        "units_est_volume",
        "units_error_volume",
        "units_est_merged",
        "units_error_merged",
    ]].to_csv(out_path, index=False)
    
    print(f"✅ Combined floor & units verification CSV saved to {out_path}")

    # ------------------------------------------
    # Build error count distributions
    # ------------------------------------------
    merged_errors = merged["units_error_merged"].value_counts().sort_index()
    meters_errors = merged["units_error_meters"].value_counts().sort_index()
    volume_errors = merged["units_error_volume"].value_counts().sort_index()
    floor_errors = merged["floor_error"].value_counts().sort_index()

    # ------------------------------------------
    # Compute & print summary statistics
    # ------------------------------------------
    print("\n================ Error Summary ================")
    for name, series in [
        ("Units (merged)", merged["units_error_merged"]),
        ("Units (meters)", merged["units_error_meters"]),
        ("Units (volume)", merged["units_error_volume"]),
        ("Floors", merged["floor_error"]),
    ]:
        mean_val = series.mean()
        sd_val = series.std()
        print(f"{name} Error: mean = {mean_val:.2f}, sd = {sd_val:.2f}")
    print("================================================\n")

    # ------------------------------------------
    # Plot 4 separate graphs
    # ------------------------------------------
    plot_error_distribution(floor_errors,
                            title="Floors: Estimated - Actual",
                            xlabel="floors_est - Number of Floors")

    plot_error_distribution(meters_errors,
                            title="Doorbells vs Units (Meters)",
                            xlabel="units_est_meters - Doorbells")

    plot_error_distribution(volume_errors,
                            title="Doorbells vs Units (Volume)",
                            xlabel="units_est_volume - Doorbells")

    plot_error_distribution(merged_errors,
                            title="Doorbells vs Units (Merged)",
                            xlabel="units_est_merged - Doorbells")

    return merged


if __name__ == "__main__":
    df = main()
