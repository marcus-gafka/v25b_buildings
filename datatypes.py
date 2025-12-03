from dataclasses import dataclass, field
from shapely.geometry import Point, shape   
from typing import List, Optional

@dataclass
class Meter:
    id: int
    componenti: Optional[int] = None
    consumo_2024: Optional[float] = None

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
    has_hotel: Optional[bool] = None

    full_alias: Optional[str] = None
    short_alias: Optional[str] = None
    alias_segment: Optional[int] = None

    qu_terra: Optional[float] = None
    qu_gronda: Optional[float] = None

    tp_cls: Optional[str] = None
    tipo_fun: Optional[str] = None
    spec_fun: Optional[str] = None

    height: Optional[float] = None
    superficie: Optional[float] = None
    normalized_height: Optional[float] = None
    normalized_superficie: Optional[float] = None
    livable_space: Optional[float] = None

    floors_est: Optional[int] = None
    units_est_meters: Optional[int] = None
    units_est_volume: Optional[int] = None
    units_est_merged: Optional[int] = None
    pop_est: Optional[int] = None

    full_nr: Optional[bool] = None
    units_str: Optional[int] = None
    units_empty: Optional[int] = None
    units_primary: Optional[int] = None
    units_secondary: Optional[int] = None
    units_res: Optional[int] = None
    units_calc: Optional[int] = None

    measured: Optional[bool] = None
    surveyed: Optional[bool] = None

@dataclass
class Tract:
    id: str
    buildings: List[Building] = field(default_factory=list)

    full_alias: Optional[str] = None
    alias_segment: Optional[str] = None

    pop21: Optional[int] = None
    abi21: Optional[int] = None
    fam21: Optional[int] = None
    edi21: Optional[int] = None

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