from typing import List, Union
from datatypes import Tract, Island, Sestiere

def return_actual_population(data: Union[Tract, Island, Sestiere, List[Tract], List[Island], List[Sestiere]]):
    """
    Counts total population per Sestiere and prints the grand total.
    Can accept:
      - a single Tract, Island, or Sestiere
      - a list of Tracts, Islands, or Sestieres
    """
    # Normalize input to a list of tracts
    tracts: List[Tract] = []

    if isinstance(data, Tract):
        tracts = [data]
    elif isinstance(data, Island):
        tracts = getattr(data, "tracts", [])  # assume Island has a list of tracts
    elif isinstance(data, Sestiere):
        tracts = []
        for isl in getattr(data, "islands", []):
            tracts.extend(getattr(isl, "tracts", []))
    elif isinstance(data, list):
        if not data:
            tracts = []
        elif isinstance(data[0], Tract):
            tracts = data
        elif isinstance(data[0], Island):
            for isl in data:
                tracts.extend(getattr(isl, "tracts", []))
        elif isinstance(data[0], Sestiere):
            for s in data:
                for isl in getattr(s, "islands", []):
                    tracts.extend(getattr(isl, "tracts", []))
        else:
            raise TypeError("List elements must be Tract, Island, or Sestiere")
    else:
        raise TypeError("Input must be Tract, Island, Sestiere or list of them")

    # Sum populations
    sestiere_pop = {}
    grand_total = 0
    for tract in tracts:
        s_name = tract.island.sestiere.raw
        pop = tract.population
        sestiere_pop[s_name] = sestiere_pop.get(s_name, 0) + pop
        grand_total += pop

    # Print
    print("Population by Sestiere:")
    for s_name, pop in sestiere_pop.items():
        print(f"  {s_name}: {pop}")
    print(f"Grand total population: {grand_total}")

    return grand_total

def return_estimated_population(data: Union[Tract, Island, Sestiere, List[Tract], List[Island], List[Sestiere]]):
    """
    Counts total *estimated* population per Sestiere based on building.pop_est.
    Can accept:
      - a single Tract, Island, or Sestiere
      - a list of Tracts, Islands, or Sestieres
    Returns the grand total estimated population.
    """
    # Normalize input to a list of tracts
    tracts: List[Tract] = []

    if isinstance(data, Tract):
        tracts = [data]
    elif isinstance(data, Island):
        tracts = getattr(data, "tracts", [])
    elif isinstance(data, Sestiere):
        tracts = []
        for isl in getattr(data, "islands", []):
            tracts.extend(getattr(isl, "tracts", []))
    elif isinstance(data, list):
        if not data:
            tracts = []
        elif isinstance(data[0], Tract):
            tracts = data
        elif isinstance(data[0], Island):
            for isl in data:
                tracts.extend(getattr(isl, "tracts", []))
        elif isinstance(data[0], Sestiere):
            for s in data:
                for isl in getattr(s, "islands", []):
                    tracts.extend(getattr(isl, "tracts", []))
        else:
            raise TypeError("List elements must be Tract, Island, or Sestiere")
    else:
        raise TypeError("Input must be Tract, Island, Sestiere or list of them")

    # Sum estimated populations
    sestiere_pop = {}
    grand_total = 0
    for tract in tracts:
        s_name = tract.island.sestiere.raw
        total_est = sum(b.pop_est or 0 for b in tract.buildings)
        sestiere_pop[s_name] = sestiere_pop.get(s_name, 0) + total_est
        grand_total += total_est

    # Print breakdown
    print("Estimated population by Sestiere:")
    for s_name, pop in sestiere_pop.items():
        print(f"  {s_name}: {int(pop)}")
    print(f"Grand total estimated population: {int(grand_total)}")

    return grand_total
