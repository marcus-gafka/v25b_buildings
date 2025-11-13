from pathlib import Path
import matplotlib.pyplot as plt
from dataset import Dataset
from plotter import plot_island_bw
from constants import FIELDWORK_DIR, DATA_DIR

def generate_bw_maps():
    geojson_path = DATA_DIR / "VPC_Buildings_With_Aliases.geojson"
    print("📂 Loading dataset...")
    ds = Dataset(geojson_path)
    # Already called in constructor, no need for ds._build_hierarchy() if constructor does it

    for s in ds.venice.sestieri:
        for island in s.islands:
            s_code = s.code[:2].upper()
            i_code = island.code.upper()
            filename = f"{s_code}-{i_code}-F.png"
            filepath = FIELDWORK_DIR / filename

            print(f"🗺️ Generating {filename}...")

            try:
                plt.ioff()
                # --- Generate the map but do NOT show ---
                fig, ax = plot_island_bw(ds, i_code, figsize=(12, 12), show=False)
                # --- Save that figure ---
                plt.savefig(filepath, bbox_inches="tight", dpi=300)
                plt.close(fig)
                print(f"✅ Saved {filepath.name}")
            except Exception as e:
                print(f"❌ Failed for {i_code}: {e}")

    print("🎉 All black-and-white maps generated!")

if __name__ == "__main__":
    generate_bw_maps()
