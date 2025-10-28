import json
from collections import defaultdict
import os

# --- Input file ---
GEOJSON_FILE = "V25B_Buildings_Primary_Building_Dataset.geojson"

def load_geojson(filepath):
    """Load GeoJSON data"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_population_by_sestiere(data):
    """
    Sum population by sestiere, avoiding double-counting census tracts.
    """
    sestiere_to_census = defaultdict(set)
    census_population = {}

    for feature in data["features"]:
        props = feature["properties"]

        sestiere = props.get("Nome_Sesti")
        census_id = props.get("Sez_Cen91")
        population = props.get("POP21")

        # Skip if any key is missing
        if sestiere and census_id and population is not None:
            census_population[census_id] = population
            sestiere_to_census[sestiere].add(census_id)

    # Compute total population per sestiere
    sestiere_pop = {}
    for sestiere, census_ids in sestiere_to_census.items():
        total = sum(census_population[cid] for cid in census_ids)
        sestiere_pop[sestiere] = total

    return sestiere_pop

def main():
    data = load_geojson(GEOJSON_FILE)
    sestiere_pop = compute_population_by_sestiere(data)

    print("\nTotal population by sestiere:\n")
    grand_total = 0
    for sestiere, pop in sorted(sestiere_pop.items()):
        print(f"{sestiere}: {pop:,}")
        grand_total += pop

    print("\nVenice Total Population: {:,}\n".format(grand_total))

if __name__ == "__main__":
    main()
