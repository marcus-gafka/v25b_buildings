from dataset import Dataset
from constants import ALIAS_GEOJSON
from plotter import plot_sestiere_w_str

def main():
    print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
    ds = Dataset(str(ALIAS_GEOJSON))

    print("✅ Dataset loaded. Venice hierarchy ready.")
    
    sestiere_code = "SP"

    print(f"📊 Plotting sestiere: {sestiere_code}")
    plot_sestiere_w_str(ds, sestiere_code)

    print("🎉 Done.")

if __name__ == "__main__":
    main()
