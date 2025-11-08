from dataclasses import dataclass, field
from pathlib import Path
from shapely.geometry import shape, Point
from typing import List, Optional
from constants import BUILDING_FIELD, TRACT_FIELD, ISLAND_FIELD, SESTIERE_FIELD
from datatypes import Building, Tract, Island, Sestiere, Venice
from file_utils import load_geojson

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

    # === Hierarchy Construction ===
    def _build_hierarchy(self) -> Venice:
        sestiere_map = {}

        for idx, f in enumerate(self.features, start=1):
            props = f.get("properties", {})
            geom = f.get("geometry")

            s_name = self._normalize_str(props.get(SESTIERE_FIELD)) or "Unknown"
            i_code = self._normalize_str(props.get(ISLAND_FIELD)) or "0"
            t_id = self._normalize_str(props.get(TRACT_FIELD)) or "0"
            b_id = props.get(BUILDING_FIELD, idx)

            # --- Geometry / Centroid ---
            centroid = None
            try:
                geom_shape = shape(geom)
                centroid = geom_shape.centroid if geom_shape else None
            except Exception:
                pass

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
            )
            tract.buildings.append(building)

        return Venice(sestieri=list(sestiere_map.values()))
