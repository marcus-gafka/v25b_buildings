from dataset import Dataset
from constants import ALIAS_GEOJSON
from plotter import plot_island

ds_alias = Dataset(ALIAS_GEOJSON)
plot_island(ds_alias, "MELO")