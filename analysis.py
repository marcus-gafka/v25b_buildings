from dataset import Dataset
from constants import ALIAS_GEOJSON
from plotter import plot_island, plot_islands_with_snakes, plot_island_bw

ds_alias = Dataset(ALIAS_GEOJSON)
#plot_island(ds_alias, "MELO")
plot_island_bw(ds_alias, "MELO")
#plot_islands_with_snakes(ds_alias, "CERC")