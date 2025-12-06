from dataset import Dataset
from constants import ALIAS_GEOJSON, ESTIMATES_DIR
import matplotlib.pyplot as plt

from estimation_null import estimation_null
from estimation_v0 import estimation_v0
from estimation_v1 import estimation_v1
from estimation_v2 import estimation_v2
from estimation_v3 import estimation_v3
from estimation_v4 import estimation_v4

from file_utils import csv_to_geojson

def main():

    ds = Dataset(str(ALIAS_GEOJSON))
    #estimation_v4(ds,{"PALA"},False)
    estimation_v4(ds,{})
    ds.export_hierarchy_text(ESTIMATES_DIR / "Venice_hierarchy.txt")
    csv_to_geojson(ESTIMATES_DIR / "VPC_Estimates_V4.csv")

if __name__ == "__main__":
    main()