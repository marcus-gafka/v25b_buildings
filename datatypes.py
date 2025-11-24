from dataclasses import dataclass, field
from shapely.geometry import Point, shape   
from typing import List, Optional

@dataclass
class Meter:
    id: int

@dataclass
class Address:
    address: str
    meters: List[Meter] = field(default_factory=list)
    strs: List[int] = field(default_factory=list)
    hotels: List[int] = field(default_factory=list)
    hotels_extras: List[int] = field(default_factory=list)

@dataclass
class Building:
    id: int
    centroid: Point
    geometry: shape
    addresses: List[Address] = field(default_factory=list)

    full_alias: Optional[str] = None
    short_alias: Optional[str] = None
    alias_segment: Optional[int] = None

    height: Optional[float] = None

    floors_est: Optional[int] = None
    units_est: Optional[int] = None
    pop_est: Optional[int] = None

@dataclass
class Tract:
    id: str
    buildings: List[Building] = field(default_factory=list)

    full_alias: Optional[str] = None
    alias_segment: Optional[str] = None

    pop21: Optional[int] = None

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
