from dataset import Dataset
from constants import ALIAS_GEOJSON, ESTIMATES_DIR
import matplotlib.pyplot as plt

from estimation_null import estimation_null
from estimation_v0 import estimation_v0
from estimation_v1 import estimation_v1
from estimation_v2 import estimation_v2
from estimation_v3 import estimation_v3

from file_utils import csv_to_geojson

def main():

    print(f"📂 Loading building GeoJSON: {ALIAS_GEOJSON.name}")
    ds = Dataset(str(ALIAS_GEOJSON))
    estimation_v3(ds,{},True)
    #estimation_v3(ds, {"MELO", "ZACC"})
    csv_to_geojson(ESTIMATES_DIR / "VPC_Estimates_V3.csv")

if __name__ == "__main__":
    main()