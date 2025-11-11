from dataset import Dataset
from constants import FILTERED_GEOJSON, ALIAS_GEOJSON
from plotter import plot_island

#ds = Dataset(FILTERED_GEOJSON)
ds_alias = Dataset(ALIAS_GEOJSON)

#ds_alias.sestieri["SM"].islands[0].verbose()
plot_island(ds_alias, "MELO")