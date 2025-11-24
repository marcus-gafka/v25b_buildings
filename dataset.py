from dataclasses import dataclass, field
from pathlib import Path
from shapely.geometry import shape
from typing import List, Optional
from constants import BUILDING_FIELD, TRACT_FIELD, ISLAND_FIELD, SESTIERE_FIELD,FILTERED_ADDRESS_CSV,FILTERED_WATER_CSV,FILTERED_HOTEL_CSV,FILTERED_HOTELS_EXTRA_CSV,FILTERED_STR_CSV
from datatypes import Meter, Address, Building, Tract, Island, Sestiere, Venice
from file_utils import load_geojson
import pandas as pd

@dataclass
class Dataset:
    features: List[dict] = field(default_factory=list)
    venice: Optional[Venice] = None
    source: Optional[str] = None

    def __init__(self, geojson_path: str):
        path = Path(geojson_path)
        if not path.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {path}")

        print(f"📂 Loading GeoJSON: {path.name}")
        data = load_geojson(str(path))
        self.features = data.get("features", [])
        self.source = str(path)
        print(f"✅ Loaded {len(self.features)} features")

        self.venice = self._build_hierarchy()
        print(f"🏗️ Built hierarchy with {len(self.venice.sestieri)} sestieri")

    # === Helpers ===
    def _normalize_str(self, raw):
        if raw is None:
            return ""
        s = str(raw).strip()
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            s = s[1:-1].strip()
        return s

    def _build_hierarchy(self) -> Venice:
        addr_df = pd.read_csv(FILTERED_ADDRESS_CSV)
        water_df = pd.read_csv(FILTERED_WATER_CSV)
        hotels_df = pd.read_csv(FILTERED_HOTEL_CSV)
        hotels_extra_df = pd.read_csv(FILTERED_HOTELS_EXTRA_CSV)
        str_df = pd.read_csv(FILTERED_STR_CSV)

        # Standardize addresses
        addr_df["Full_sesti"] = addr_df["Full_sesti"].astype(str).str.strip().str.upper()
        water_df["ProcessedAddress"] = water_df["ProcessedAddress"].astype(str).str.strip().str.upper()
        hotels_df["ADDRESS"] = hotels_df["ADDRESS"].astype(str).str.strip().str.upper()
        hotels_extra_df["ADDRESS"] = hotels_extra_df["ADDRESS"].astype(str).str.strip().str.upper()
        str_df["ADDRESS"] = str_df["ADDRESS"].astype(str).str.strip().str.upper()

        # Create address → FIDs mapping for meters, hotels, hotels_extra, STRs
        meters_map = water_df.groupby("ProcessedAddress")["FID"].apply(list).to_dict()
        hotels_map = hotels_df.groupby("ADDRESS")["FID"].apply(list).to_dict()
        hotels_extra_map = hotels_extra_df.groupby("ADDRESS")["FID"].apply(list).to_dict()
        strs_map = str_df.groupby("ADDRESS")["FID"].apply(list).to_dict()

        # -------------------------------
        # Start building hierarchy
        # -------------------------------
        sestiere_map = {}
        building_map = {}  # building id → Building object for easy lookup

        for idx, feature in enumerate(self.features, start=1):
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            # --- Normalize fields safely ---
            s_name = str(props.get(SESTIERE_FIELD, "Unknown")).strip()
            i_code = str(props.get(ISLAND_FIELD, "0")).strip()
            t_id = str(props.get(TRACT_FIELD, "0")).strip()
            b_id = props.get(BUILDING_FIELD, idx)

            # --- Geometry ---
            try:
                geom_shape = shape(geom)
                centroid = geom_shape.centroid if geom_shape else None
            except Exception:
                geom_shape = None
                centroid = None

            # --- Sestiere ---
            if s_name not in sestiere_map:
                s_code = s_name[:2].upper() if s_name != "Unknown" else "00"
                sestiere_map[s_name] = Sestiere(code=s_code, name=s_name)
            sestiere = sestiere_map[s_name]

            # --- Island ---
            island = next((i for i in sestiere.islands if i.code == i_code), None)
            if island is None:
                island = Island(code=i_code, name=i_code)
                sestiere.islands.append(island)

            # --- Tract ---
            tract_key = f"{i_code}_{t_id}"
            tract = next((t for t in island.tracts if t.id == tract_key), None)
            if tract is None:
                tract = Tract(id=tract_key)
                island.tracts.append(tract)

            # --- Building ---
            building = Building(
                id=b_id,
                centroid=centroid,
                geometry=geom_shape,
                full_alias=props.get("full_alias"),
                short_alias=props.get("short_alias"),
                alias_segment=props.get("alias_segment"),
                height=props.get("height"),
                floors_est=props.get("floors_est"),
                units_est=props.get("units_est"),
                pop_est=props.get("pop_est"),
            )
            tract.buildings.append(building)
            building_map[b_id] = building

        # -------------------------------
        # Attach addresses + meters/hotels/STRs
        # -------------------------------
        for _, row in addr_df.iterrows():
            b_id = row["TARGET_FID_12_13"]
            addr_code = row["Full_sesti"].strip().upper()
            building = building_map.get(b_id)
            if building is None:
                continue

            # Create Address object
            address_obj = Address(
                address=addr_code,
                meters=[Meter(fid) for fid in meters_map.get(addr_code, [])],
                hotels=hotels_map.get(addr_code, []),
                hotels_extras=hotels_extra_map.get(addr_code, []),
                strs=strs_map.get(addr_code, [])
            )
            building.addresses.append(address_obj)

        return Venice(sestieri=list(sestiere_map.values()))