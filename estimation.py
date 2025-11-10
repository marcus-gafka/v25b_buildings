import math

# === Architectural code mappings based on your table ===
ARCH_CODE_UNITS = {
    # Monocellular
    "A": 1,
    "A1": 1,
    "Ka/A": 1,
    "Ka/A1": 1,
    "Knt/A1": 1,
    # Bicellular
    "B": 2,
    "B/SU": 2,
    "B1": 2,
    "Bg": 2,
    "Ka/B": 2,
    "Koa/B": 2,
    "Kt/B": 2,
    # Tricellular
    "C": 3,
    "C/knt": 3,
    "C/Nd": 3
}

# Floor height estimate in meters
FLOOR_HEIGHT = 3.0

# Average unit area for fallback
AVERAGE_UNIT_AREA = 50  # square meters, adjust as needed

def estimate_floors(row) -> int:
    try:
        qu_gronda = float(row.get("Qu_Gronda", 0))
        floors = math.ceil(qu_gronda / FLOOR_HEIGHT)
        return max(1, floors)
    except Exception:
        return 1  # fallback default

def estimate_units(row) -> int:
    floors = row.get("floors_est", 1)
    tp_cls = str(row.get("TP_CLS_ED", "")).upper()
    footprint = float(row.get("Superficie", 0))

    usable_floors = max(0, floors - 1)

    # Check architectural code mapping
    units_per_floor = ARCH_CODE_UNITS.get(tp_cls)
    if units_per_floor is None:
        # fallback: footprint / average unit area
        units_per_floor = max(1, round(footprint / AVERAGE_UNIT_AREA)) if footprint > 0 else 1

    return usable_floors * units_per_floor
