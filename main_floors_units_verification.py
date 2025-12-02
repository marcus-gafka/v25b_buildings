import pandas as pd
from pathlib import Path
from constants import FILTERED_SURVEY_CSV, ESTIMATES_DIR
import matplotlib.pyplot as plt

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
    est_path = ESTIMATES_DIR / "VPC_Estimates_V3.csv"
    est_df = pd.read_csv(est_path)

    print("🔗 Merging datasets…")
    merged = survey_df.merge(est_df, on="short_alias", how="left")

    # ------------------------------------------
    # Compute all errors
    # ------------------------------------------
    merged["floor_error"] = merged["floors_est"] - merged["Number of Floors"]
    merged["units_error_meters"] = merged["units_est_meters"] - merged["Number of Doorbells"]
    merged["units_error_volume"] = merged["units_est_volume"] - merged["Number of Doorbells"]

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

    ]].to_csv(out_path, index=False)
    
    print(f"✅ Combined floor & units verification CSV saved to {out_path}")

    # ------------------------------------------
    # Build error count distributions
    # ------------------------------------------
    floor_errors  = merged["floor_error"].value_counts().sort_index()
    meters_errors = merged["units_error_meters"].value_counts().sort_index()
    volume_errors = merged["units_error_volume"].value_counts().sort_index()

    # ------------------------------------------
    # Color function (0 = green, farther = red)
    # ------------------------------------------
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

    # Example: build color lists for each graph using its own max error
    floor_max = max(abs(floor_errors.index).max(), 1)
    meters_max = max(abs(meters_errors.index).max(), 1)
    volume_max = max(abs(volume_errors.index).max(), 1)

    floor_colors  = [error_to_color(e, floor_max) for e in floor_errors.index]
    meters_colors = [error_to_color(e, meters_max) for e in meters_errors.index]
    volume_colors = [error_to_color(e, volume_max) for e in volume_errors.index]

    # ------------------------------------------
    # Plot: 3 side-by-side bar charts
    # ------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)

    # Floors
    axes[0].bar(floor_errors.index, floor_errors.values,
                color=floor_colors, edgecolor='black')
    axes[0].set_title("Floor Estimate Errors")
    axes[0].set_xlabel("floors_est - observed floors")
    axes[0].set_ylabel("Number of Buildings")
    axes[0].grid(axis='y', alpha=0.6)

    # Units (meters) vs Doorbells
    axes[1].bar(meters_errors.index, meters_errors.values,
                color=meters_colors, edgecolor='black')
    axes[1].set_title("Doorbells vs Units (Meters)")
    axes[1].set_xlabel("units_est_meters - Doorbells")
    axes[1].grid(axis='y', alpha=0.6)


    # Units (volume) vs Doorbells
    axes[2].bar(volume_errors.index, volume_errors.values,
                color=volume_colors, edgecolor='black')
    axes[2].set_title("Doorbells vs Units (Volume)")
    axes[2].set_xlabel("units_est_volume - Doorbells")
    axes[2].grid(axis='y', alpha=0.6)

    plt.tight_layout()
    plt.show()

    # ------------------------------------------
    # Compute & print summary statistics
    # ------------------------------------------

    floor_mean  = merged["floor_error"].mean()
    floor_sd    = merged["floor_error"].std()

    meters_mean = merged["units_error_meters"].mean()
    meters_sd   = merged["units_error_meters"].std()

    volume_mean = merged["units_error_volume"].mean()
    volume_sd   = merged["units_error_volume"].std()

    print("\n================ Error Summary ================")
    print(f"Floors Error:           mean = {floor_mean:.2f},  sd = {floor_sd:.2f}")
    print(f"Units (meters) Error:   mean = {meters_mean:.2f}, sd = {meters_sd:.2f}")
    print(f"Units (volume) Error:   mean = {volume_mean:.2f}, sd = {volume_sd:.2f}")
    print("================================================\n")

    return merged

if __name__ == "__main__":
    df = main()
