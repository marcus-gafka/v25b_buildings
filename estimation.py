from typing import Union, List
import math
from datatypes import Sestiere, Island, Tract, Building  # update to your module path

# --- CONFIGURATION ---
FLOOR_HEIGHT = 2.5      # meters per floor
MAX_HEIGHT = 50         # cap for building height
MAX_FOOTPRINT = 5000    # cap for footprint

# --- HELPER FUNCTIONS ---
def mean_without_outliers(values: List[float], m: float = 2.0) -> float:
    """Compute mean excluding values > m * median."""
    if not values:
        return 0
    median = sorted(values)[len(values)//2]
    filtered = [v for v in values if v <= median * m]
    if not filtered:
        return sum(values)/len(values)  # fallback
    return sum(filtered) / len(filtered)

def calculation_v0(building: Building, total_pop: float, buildings: List[Building]) -> float:
    """Evenly splits tract population across all buildings."""
    if not buildings:
        return 0
    return total_pop / len(buildings)

def calculation_v1(building: Building, total_pop: float, total_usable: float) -> float:
    """Allocate population proportionally by usable area."""
    if total_usable == 0:
        return 0
    floors = max(1, int(math.ceil(building.height / FLOOR_HEIGHT)))
    usable = building.footprint * floors
    return total_pop * (usable / total_usable)

# -----------------------
def estimate_population(target: Union[Sestiere, Island, Tract], method: str = "v1"):
    """
    Estimates population for each building in a given Sestiere, Island, or Tract.
    method: "v0" = even split, "v1" = proportional by usable area
    """
    # Collect all tracts in the target
    tracts: List[Tract] = []
    if isinstance(target, Sestiere):
        for island in target.islands:
            tracts.extend(island.tracts)
    elif isinstance(target, Island):
        tracts.extend(target.tracts)
    elif isinstance(target, Tract):
        tracts.append(target)
    else:
        raise ValueError("Target must be a Sestiere, Island, or Tract object.")

    # Estimate population per tract
    for tract in tracts:
        if not tract.buildings:
            continue

        total_pop = tract.population or 0

        if method == "v0":
            # Simple even split across all buildings
            for b in tract.buildings:
                b.pop_est = calculation_v0(b, total_pop, tract.buildings)

        elif method == "v1":
            # Filter R-type buildings (residential)
            residential_buildings = [
                b for b in tract.buildings if b.typology and b.typology.startswith("R")
            ]

            if not residential_buildings:
                # fallback to even split if no valid residential buildings
                for b in tract.buildings:
                    b.pop_est = calculation_v0(b, total_pop, tract.buildings)
                continue

            # Compute height and footprint averages excluding outliers (>2x median or zero)
            heights = [b.height for b in residential_buildings if b.height and b.height > 0]
            footprints = [b.footprint for b in residential_buildings if b.footprint and b.footprint > 0]

            avg_height = mean_without_outliers(heights) if heights else FLOOR_HEIGHT
            avg_footprint = mean_without_outliers(footprints) if footprints else 100.0

            # Replace outliers or zero values with tract average
            for b in residential_buildings:
                if not b.height or b.height <= 0 or b.height > avg_height * 2:
                    b.height = avg_height
                if not b.footprint or b.footprint <= 0 or b.footprint > avg_footprint * 2:
                    b.footprint = avg_footprint

            # Compute total usable area
            total_usable = sum(
                min(b.footprint, MAX_FOOTPRINT) *
                max(1, int(math.ceil(min(b.height, MAX_HEIGHT) / FLOOR_HEIGHT)))
                for b in residential_buildings
            )

            if total_usable == 0:
                # fallback to even split if all usable areas are zero
                for b in tract.buildings:
                    b.pop_est = calculation_v0(b, total_pop, tract.buildings)
                continue

            # Allocate population proportionally to usable area
            for b in tract.buildings:
                if b in residential_buildings:
                    floors = max(1, int(math.ceil(min(b.height, MAX_HEIGHT) / FLOOR_HEIGHT)))
                    usable = min(b.footprint, MAX_FOOTPRINT) * floors
                    b.pop_est = total_pop * (usable / total_usable)
                else:
                    b.pop_est = 0
        else:
            raise ValueError("Invalid method. Choose 'v0' or 'v1'.")


# -----------------------
def estimate_all(dataset, method: str = "v1"):
    """Estimate populations for all sestieri in dataset."""
    for s in dataset.sestieres:
        estimate_population(s, method=method)
    print(f"✅ Population estimation complete for all sestieri using method '{method}'.")

# -----------------------
def print_building_population(buildings: List[Building]):
    """Print buildings with estimated population, rounded to 2 decimals."""
    for b in buildings:
        print(f"{b.alias:12} | Height: {b.height:.2f} | Footprint: {b.footprint:.2f} | "
              f"Typology: {b.typology:<10} | Est: {b.pop_est:.2f}")
