from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum
from shapely.geometry import Polygon
import json
import os
from collections import defaultdict
from math import hypot
import csv
from pathlib import Path

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# --- Sestiere enum ---
class SestiereCode(Enum):
    Cannaregio = "CN"
    Castello = "CS"
    Dorsoduro = "DD"
    SanMarco = "SM"
    SanPolo = "SP"
    SantaCroce = "SC"
    Giudecca = "GC"

    @classmethod
    def from_name(cls, name: str) -> str:
        if not name:
            return "??"
        key = name.replace(" ", "")
        try:
            return cls[key].value
        except KeyError:
            return "??"

# --- Helper function for 2-letter codes ---
def index_to_two_letter_code(index: int) -> str:
    if index < 1:
        raise ValueError("Index must be 1 or greater")
    index -= 1
    first = index // 26
    second = index % 26
    return chr(65 + first) + chr(65 + second)

# --- Core dataclasses ---
@dataclass
class Coord:
    x: float
    y: float

@dataclass
class Sestiere:
    raw: str
    code: str = ""
    alias: Optional[str] = None
    islands: List["Island"] = field(default_factory=list)

    def __post_init__(self):
        self.code = SestiereCode.from_name(self.raw)

    def generate_alias(self):
        self.alias = self.code
        return self.alias

@dataclass
class Island:
    raw: str
    centroid: Coord
    sestiere: Sestiere
    code: str = ""
    alias: Optional[str] = None
    tracts: List["Tract"] = field(default_factory=list)

    def generate_alias(self):
        self.alias = f"{self.sestiere.generate_alias()}-{self.code}"
        return self.alias

@dataclass
class Tract:
    raw: int
    centroid: Coord
    population: int
    island: Island
    code: str = ""
    alias: Optional[str] = None
    buildings: List["Building"] = field(default_factory=list)

    def generate_alias(self):
        self.alias = f"{self.island.generate_alias()}-{self.code}"
        return self.alias

@dataclass
class Address:
    full: str
    ses: str
    num: int

    @property
    def addy(self):
        return f"{self.ses} {self.num}"

@dataclass
class Building:
    row: int
    polygon: List[Coord]
    tract: Tract
    number: int = 0
    alias: Optional[str] = None
    pop_est: Optional[int] = None
    addresses: List[Address] = field(default_factory=list)

    typology: Optional[str] = None
    height: Optional[float] = None
    footprint: Optional[float] = None

    @property
    def centroid(self):
        poly = Polygon([(c.x, c.y) for c in self.polygon])
        c = poly.centroid
        return Coord(c.x, c.y)

    def generate_alias(self):
        self.alias = f"{self.tract.generate_alias()}-{self.number:02d}"
        return self.alias

def assign_island_codes(islands: List[Island]):
    sorted_islands = sorted(islands, key=lambda i: i.centroid.x)
    for idx, isl in enumerate(sorted_islands, start=1):
        isl.code = index_to_two_letter_code(idx)
        isl.generate_alias()

def assign_tract_codes(tracts: List[Tract]):
    sorted_tracts = sorted(tracts, key=lambda t: t.centroid.x)
    for idx, t in enumerate(sorted_tracts, start=1):
        t.code = index_to_two_letter_code(idx)
        t.generate_alias()

def weighted_building_order(buildings: List[Building], west_weight=1.0, dist_weight=1.0):
    if not buildings:
        return []
    remaining = buildings.copy()
    current = min(remaining, key=lambda b: b.centroid.x)
    ordered = [current]
    remaining.remove(current)
    while remaining:
        def score(b, current=current):
            west_score = west_weight * (b.centroid.x - current.centroid.x)
            dist_score = dist_weight * hypot(b.centroid.x - current.centroid.x,
                                             b.centroid.y - current.centroid.y)
            return west_score + dist_score
        next_b = min(remaining, key=score)
        ordered.append(next_b)
        remaining.remove(next_b)
        current = next_b
    return ordered

# --- Dataset class ---
@dataclass
class Dataset:
    geojson_file: Optional[str] = None
    csv_file: Optional[str] = None
    features: List[dict] = field(default_factory=list)
    sestieres: List[Sestiere] = field(default_factory=list)
    buildings: List[Building] = field(default_factory=list)

    def load_geojson(self):
        with open(self.geojson_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.features = data.get("features", [])
        # auto-assign CSV path if not already set
        if self.csv_file is None:
            base, _ = os.path.splitext(self.geojson_file)
            self.csv_file = base + ".csv"

    def load_csv(self):
        """Load features from a CSV file and reconstruct row IDs properly."""
        import csv, json, ast, os

        if not self.csv_file:
            raise ValueError("CSV file path not set.")

        with open(self.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            features = []

            for row in reader:
                # Extract geometry
                geom_type = row.pop("geometry_type", None)
                coords_str = row.pop("geometry_coordinates", "[]")
                try:
                    coords = json.loads(coords_str)
                except json.JSONDecodeError:
                    try:
                        coords = ast.literal_eval(coords_str)
                    except Exception:
                        coords = []

                # Convert numeric fields
                props = {}
                for k, v in row.items():
                    if v == "":
                        props[k] = None
                    elif k in ["ID", "SEZ21_ID", "POP21", "FAM21", "ABI21", "EDI21"]:
                        try:
                            props[k] = int(v)
                        except ValueError:
                            props[k] = None
                    else:
                        props[k] = v

                # Build the feature
                feature = {
                    "type": "Feature",
                    "properties": props,
                    "geometry": {
                        "type": geom_type or "Polygon",
                        "coordinates": coords
                    }
                }
                features.append(feature)

        self.features = features

        # auto-assign GeoJSON path if not already set
        if self.geojson_file is None:
            base, _ = os.path.splitext(self.csv_file)
            self.geojson_file = base + ".geojson"

        print(f"✅ Loaded {len(features)} features from {self.csv_file}")

    def build_hierarchy(self):
        """Build hierarchy and assign aliases if they don't exist."""
        if not self.features:
            self.load_geojson()

        s_dict: Dict[str, Sestiere] = {}
        i_dict: Dict[str, Island] = {}
        t_dict: Dict[str, Tract] = {}
        b_list: List[Building] = []

        for f in self.features:
            props = f.get("properties", {})
            s_name = props.get("Nome_Sesti")
            s = s_dict.setdefault(s_name, Sestiere(raw=s_name))

            i_name = props.get("Sesti_Isole")
            island_key = f"{s_name}-{i_name}"
            if island_key not in i_dict:
                centroid = Coord(float(props.get("Xc", 0)), float(props.get("Yc", 0)))
                i_dict[island_key] = Island(raw=i_name, centroid=centroid, sestiere=s)
                s.islands.append(i_dict[island_key])
            i = i_dict[island_key]

            t_num = int(props.get("SEZ21_ID", 0))
            tract_key = f"{i_name}-{t_num}"
            if tract_key not in t_dict:
                centroid = Coord(float(props.get("Xc", 0)), float(props.get("Yc", 0)))
                pop = int(props.get("POP21", 0))
                t_dict[tract_key] = Tract(raw=t_num, centroid=centroid, population=pop, island=i)
                i.tracts.append(t_dict[tract_key])
            t = t_dict[tract_key]

            geom = f.get("geometry", {})
            coords: List[Coord] = []
            if geom.get("type") == "Polygon":
                for x, y in geom.get("coordinates", [[]])[0]:
                    coords.append(Coord(float(x), float(y)))
            elif geom.get("type") == "MultiPolygon":
                for x, y in geom.get("coordinates", [[[]]])[0][0]:
                    coords.append(Coord(float(x), float(y)))

            b = Building(row=int(props.get("ID") or len(b_list) + 1), polygon=coords, tract=t)
            t.buildings.append(b)
            b_list.append(b)

        # --- Alias assignment section ---
        total_buildings = len(b_list)
        j = 0
        for s in s_dict.values():
            assign_island_codes(s.islands)
            for i in s.islands:
                assign_tract_codes(i.tracts)
                for t in i.tracts:
                    ordered_buildings = weighted_building_order(t.buildings)
                    for idx, b in enumerate(ordered_buildings, start=1):
                        b.number = idx
                        b.generate_alias()
                        j += 1
                        percent = (j / total_buildings) * 100
                        print(f"Building assigned: {b.alias} / completion: {j}/{total_buildings} ({percent:.1f}%)")

        self.sestieres = list(s_dict.values())
        self.buildings = b_list

    def build_hierarchy_with_alias(self):
        """Build hierarchy using existing aliases from the GeoJSON (alias defines grouping).
        Also attaches addresses from V25B_Buildings_and_Address.csv."""
        
        print("Checking first few feature properties for alias field...")
        for i, f in enumerate(self.features[:5]):
            props = f.get("properties", {})

        if not self.features:
            self.load_geojson()

        print("Building hierarchy using ALIAS-based grouping...")

        # --- Load address CSV ---
        address_file = Path(DATA_DIR) / "V25B_Buildings_and_Address.csv"
        alias_to_addresses: dict[str, list[Address]] = {}

        if address_file.exists():
            print(f"📄 Loading addresses from {address_file.name}...")
            with open(address_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Strip headers to avoid hidden spaces
                reader.fieldnames = [name.strip() for name in reader.fieldnames]
                for row in reader:
                    alias = row.get("ALIAS")
                    full_addr = row.get("Full_sesti")
                    if not alias or not full_addr:
                        continue
                    alias_to_addresses.setdefault(alias.strip(), []).append(
                        Address(full=full_addr.strip(), ses=full_addr.strip(), num=0)
                    )
        else:
            print("⚠️ Address CSV not found — continuing without address data.")

        # --- Initialize dicts ---
        s_dict: dict[str, Sestiere] = {}
        i_dict: dict[str, Island] = {}
        t_dict: dict[str, Tract] = {}
        b_list: list[Building] = []

        # --- Build hierarchy ---
        for f in self.features:
            props = f.get("properties", {})
            alias = props.get("ALIAS")
            if not alias:
                print("⚠️ Missing alias in one or more features — skipping hierarchy build.")
                return

            parts = alias.split("-")
            if len(parts) < 4:
                print(f"⚠️ Invalid alias format: {alias}")
                continue

            s_code, island_code, tract_code, bldg_num = parts[:4]

            # --- Sestiere ---
            s = s_dict.setdefault(s_code, Sestiere(raw=s_code))

            # --- Island ---
            island_key = f"{s_code}-{island_code}"
            if island_key not in i_dict:
                centroid = Coord(float(props.get("Xc", 0)), float(props.get("Yc", 0)))
                i_dict[island_key] = Island(raw=island_code, centroid=centroid, sestiere=s)
                s.islands.append(i_dict[island_key])
            i = i_dict[island_key]

            # --- Tract ---
            tract_key = f"{island_key}-{tract_code}"
            if tract_key not in t_dict:
                centroid = Coord(float(props.get("Xc", 0)), float(props.get("Yc", 0)))
                pop = int(props.get("POP21", 0))
                t_dict[tract_key] = Tract(raw=tract_code, centroid=centroid, population=pop, island=i)
                i.tracts.append(t_dict[tract_key])
            t = t_dict[tract_key]

            # --- Geometry ---
            geom = f.get("geometry", {})
            coords: list[Coord] = []
            if geom.get("type") == "Polygon":
                for x, y in geom.get("coordinates", [[]])[0]:
                    coords.append(Coord(float(x), float(y)))
            elif geom.get("type") == "MultiPolygon":
                for x, y in geom.get("coordinates", [[[]]])[0][0]:
                    coords.append(Coord(float(x), float(y)))

            # --- Building ---
            b = Building(
                row=int(props.get("ID") or len(b_list) + 1),
                polygon=coords,
                tract=t,
                alias=alias,
                number=int(bldg_num),
                typology=str(props.get("Tipologia")),
                footprint=float(props.get("Superficie")),
                height=float(props.get("Qu_Gronda")),
                addresses=alias_to_addresses.get(alias, [])
            )

            t.buildings.append(b)
            b_list.append(b)

        self.sestieres = list(s_dict.values())
        self.buildings = b_list

        total_addresses = sum(len(v) for v in alias_to_addresses.values())
        print(f"✅ Hierarchy built with {len(b_list)} buildings, {total_addresses} total addresses linked.")
    
    def to_dict(self):
        """Convert the dataset hierarchy to a serializable dict."""
        return {
            "sestieres": [self._sestiere_to_dict(s) for s in self.sestieres]
        }

    def _sestiere_to_dict(self, s):
        return {
            "raw": s.raw,
            "code": s.code,
            "alias": s.alias,
            "islands": [self._island_to_dict(i) for i in getattr(s, "islands", [])]
        }

    def _island_to_dict(self, i):
        return {
            "raw": i.raw,
            "code": i.code,
            "alias": i.alias,
            "tracts": [self._tract_to_dict(t) for t in getattr(i, "tracts", [])]
        }

    def _tract_to_dict(self, t):
        return {
            "raw": t.raw,
            "code": t.code,
            "alias": t.alias,
            "population": t.population,
            "buildings": [self._building_to_dict(b) for b in getattr(t, "buildings", [])]
        }

    def _building_to_dict(self, b):
        return {
            "row": b.row,
            "number": b.number,
            "alias": b.alias,
            "polygon": [{"x": c.x, "y": c.y} for c in b.polygon],
            "addresses": [a.addy for a in getattr(b, "addresses", [])]
        }

    def save_hierarchy_json(self, file_path):
        """Save the full dataset hierarchy to a JSON file."""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"Hierarchy saved to {file_path}")

    @classmethod
    def load_hierarchy_json(cls, file_path):
        """Load a dataset hierarchy from a JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        dataset = cls(geojson_file=None)  # no raw geojson needed
        dataset.sestieres = []
        dataset.buildings = []

        for s_data in data.get("sestieres", []):
            s = Sestiere(raw=s_data["raw"], code=s_data["code"], alias=s_data.get("alias"))
            s.islands = []
            for i_data in s_data.get("islands", []):
                i = Island(raw=i_data["raw"], code=i_data["code"], alias=i_data.get("alias"), centroid=Coord(0,0), sestiere=s)
                i.tracts = []
                for t_data in i_data.get("tracts", []):
                    t = Tract(
                        raw=t_data["raw"],
                        code=t_data["code"],
                        alias=t_data.get("alias"),
                        centroid=Coord(0,0),
                        population=t_data.get("population",0),
                        island=i
                    )
                    t.buildings = []
                    for b_data in t_data.get("buildings", []):
                        b = Building(
                            row=b_data.get("row",0),
                            number=b_data.get("number",0),
                            alias=b_data.get("alias"),
                            polygon=[Coord(**c) for c in b_data.get("polygon",[])],
                            tract=t,
                            addresses=[]
                        )
                        t.buildings.append(b)
                        dataset.buildings.append(b)
                    i.tracts.append(t)
                s.islands.append(i)
            dataset.sestieres.append(s)

        print(f"Hierarchy loaded from {file_path}")
        return dataset
