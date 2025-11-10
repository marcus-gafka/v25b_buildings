from dataclasses import dataclass, field
from shapely.geometry import Point, shape   
from typing import List, Optional

@dataclass
class Building:
    id: int
    centroid: Point
    geometry: shape

    full_alias: Optional[str] = None
    short_alias: Optional[str] = None
    alias_segment: Optional[int] = None

    height: Optional[float] = None

    floors_est: Optional[float] = None
    units_est: Optional[int] = None

@dataclass
class Tract:
    id: str
    buildings: List[Building] = field(default_factory=list)

    full_alias: Optional[str] = None
    alias_segment: Optional[str] = None

    height_avg: Optional[float] = None

@dataclass
class Island:
    code: str
    name: str
    tracts: List[Tract] = field(default_factory=list)

    full_alias: Optional[str] = None
    alias_segment: Optional[str] = None

@dataclass
class Sestiere:
    code: str
    name: str
    islands: List[Island] = field(default_factory=list)

    full_alias: Optional[str] = None
    alias_segment: Optional[str] = None

@dataclass
class Venice:
    sestieri: List[Sestiere] = field(default_factory=list)
