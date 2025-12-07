import pandas as pd
from dataclasses import dataclass, field
from datatypes import Meter, Address, Building, Tract, Island, Sestiere, Venice
from file_utils import load_geojson
from pathlib import Path
from shapely.geometry import shape
from typing import List, Optional
from constants import (
    BUILDING_FIELD, 
    TRACT_FIELD, 
    ISLAND_FIELD, 
    SESTIERE_FIELD, 
    FILTERED_CSV, 
    FILTERED_ADDRESS_CSV,
    FILTERED_WATER_CSV,
    FILTERED_HOTEL_CSV,
    FILTERED_HOTELS_EXTRA_CSV,
    FILTERED_STR_CSV, 
    UNIT_INFO_CSV, 
    FILTERED_SURVEY_CSV,
    TOTAL_FIELDWORK_CSV
)

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
        building_csv = pd.read_csv(FILTERED_CSV)

        # Standardize addresses
        addr_df["Full_sesti"] = addr_df["Full_sesti"].astype(str).str.strip().str.upper()
        water_df["ProcessedAddress"] = water_df["ProcessedAddress"].astype(str).str.strip().str.upper()
        hotels_df["ADDRESS"] = hotels_df["ADDRESS"].astype(str).str.strip().str.upper()
        hotels_extra_df["ADDRESS"] = hotels_extra_df["ADDRESS"].astype(str).str.strip().str.upper()
        str_df["ADDRESS"] = str_df["ADDRESS"].astype(str).str.strip().str.upper()

        # Address → FIDs mapping
        meters_map = water_df.groupby("ProcessedAddress")["FID"].apply(list).to_dict()
        hotels_map = hotels_df.groupby("ADDRESS")["FID"].apply(list).to_dict()
        hotels_extra_map = hotels_extra_df.groupby("ADDRESS")["FID"].apply(list).to_dict()
        strs_map = str_df.groupby("ADDRESS")["FID"].apply(list).to_dict()

        # Map building CSV rows
        building_data_map = building_csv.set_index("TARGET_FID_12_13").to_dict(orient="index")

        # --- Compute tract-level ABI21 and POP21 ---
        tract_aggregates = {}
        if "ABI21" in building_csv.columns and "POP21" in building_csv.columns:
            for tract_id, group in building_csv.groupby([ISLAND_FIELD, TRACT_FIELD]):
                tract_key = f"{tract_id[0]}_{tract_id[1]}"
                abi21_val = group["ABI21"].iloc[0]
                pop21_val = group["POP21"].iloc[0]
                fam21_val = group["FAM21"].iloc[0]
                edi21_val = group["EDI21"].iloc[0]
                tract_aggregates[tract_key] = {"ABI21": abi21_val, "POP21": pop21_val, "FAM21": fam21_val, "EDI21": edi21_val}

        sestiere_map = {}
        building_map = {}

        for idx, feature in enumerate(self.features, start=1):
            props = feature.get("properties", {})
            geom = feature.get("geometry")

            s_name = str(props.get(SESTIERE_FIELD, "Unknown")).strip()
            i_code = str(props.get(ISLAND_FIELD, "0")).strip()
            t_id = str(props.get(TRACT_FIELD, "0")).strip()
            b_id = props.get(BUILDING_FIELD, idx)

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
                census_values = tract_aggregates.get(tract_key, {})
                tract.abi21 = census_values.get("ABI21", 0)
                tract.pop21 = census_values.get("POP21", 0)
                tract.fam21 = census_values.get("FAM21", 0)
                tract.edi21 = census_values.get("EDI21", 0)
                island.tracts.append(tract)

            # --- Building ---
            b_row = building_data_map.get(b_id, {})
            building = Building(
                id=b_id,
                centroid=centroid,
                geometry=geom_shape,
                full_alias=props.get("full_alias"),
                short_alias=props.get("short_alias"),
                alias_segment=props.get("alias_segment"),
                qu_terra=b_row.get("Qu_Terra"),
                qu_gronda=b_row.get("Qu_Gronda"),
                superficie=b_row.get("Superficie"),
                tp_cls=b_row.get("TP_CLS_ED"),
                spec_fun=b_row.get("SpecFun"),
                tipo_fun=b_row.get("TipoFun"),
                dest_pt_an=b_row.get("Dest_Pt_An"),
            )

            tract.buildings.append(building)
            building_map[b_id] = building

        # --- Attach addresses with meters including componenti and 2024 consumption ---
        for _, row in addr_df.iterrows():
            b_id = row["TARGET_FID_12_13"]
            addr_code = row["Full_sesti"].strip().upper()
            building = building_map.get(b_id)
            if building is None:
                continue

            # Build meters list
            meters_list = []
            for fid in meters_map.get(addr_code, []):
                meter_row = water_df[water_df["FID"] == fid]
                if not meter_row.empty:
                    comp = meter_row["Componenti"].iloc[0]
                    consumo = meter_row["Consumo_medio_2024"].iloc[0]
                    rate = meter_row["Cat_Tariffa"].iloc[0] 

                    meters_list.append(
                        Meter(
                            id=int(fid),
                            componenti=int(comp) if pd.notna(comp) else 1,
                            consumo_2024=float(consumo) if pd.notna(consumo) else 0,
                            rate=rate if pd.notna(rate) else None
                        )
                    )
                else:
                    meters_list.append(Meter(id=int(fid), componenti=1, consumo_2024=0))

            address_obj = Address(
                address=addr_code,
                meters=meters_list,
                hotels=hotels_map.get(addr_code, []),
                hotels_extras=hotels_extra_map.get(addr_code, []),
                strs=strs_map.get(addr_code, [])
            )
            building.addresses.append(address_obj)

        for building in building_map.values():
            building.has_hotel = any(
                bool(addr.hotels) or bool(addr.hotels_extras)
                for addr in building.addresses
            )
            if building.has_hotel:
                print(f"{building.id} has hotel: {[addr.hotels for addr in building.addresses]}")

        # --- Debug print hierarchy ---
        """ print("\nHierarchy Build Complete:\nVenice")
        for s in sestiere_map.values():
            print(f" ├── {s.code} ({s.name})")
            for isl in s.islands:
                print(f" │    ├── Island {isl.code}")
                for tr in isl.tracts:
                    print(f" │    │    ├── Tract {tr.id}  (Buildings: {len(tr.buildings)})")
        print("\n")"""

        return Venice(sestieri=list(sestiere_map.values()))
    
    def export_hierarchy_text(self, path: str):
        """Export Venice hierarchy to a text file with full building, address, and meter info (updated V4 fields)."""
        lines = []

        for s in self.venice.sestieri:
            lines.append(f"\nSestiere: {s.code}")
            for isl in s.islands:
                lines.append(f"\n    Island: {isl.code}")
                for tr in isl.tracts:
                    tr_alias = tr.buildings[0].full_alias or tr.buildings[0].short_alias or ''
                    lines.append(f"\n        Tract Code: {'-'.join(tr_alias.split('-')[:3])} Tract ID: {tr.id}  (Buildings: {len(tr.buildings)})")
                    lines.append(f"         POP21: {tr.pop21}, ABI21: {tr.abi21}, FAM21: {tr.fam21}, EDI21: {tr.edi21}")
                    
                    for b in tr.buildings:
                        # Safe defaults for percentages and adjusted heights
                        res_pct = getattr(b, "res_pct", 0.0) or 0.0
                        nr_pct = getattr(b, "nr_pct", 0.0) or 0.0
                        empty_pct = getattr(b, "empty_pct", 0.0) or 0.0

                        res_adj_height = getattr(b, "res_adj_height", 0.0) or 0.0
                        nr_adj_height = getattr(b, "nr_adj_height", 0.0) or 0.0
                        empty_adj_height = getattr(b, "empty_adj_height", 0.0) or 0.0

                        lines.append(f"\n            Building Alias: {b.full_alias}, {b.short_alias}, ID: {b.id}")
                        lines.append(f"                Type: {b.tp_cls}, Dest_Pt_An: {b.dest_pt_an}, Full_NR?: {b.full_nr}")
                        lines.append(f"                Height: {b.height}, NormHeight: {b.normalized_height}, FloorsEst: {b.floors_est}")
                        lines.append(f"                Superficie: {b.superficie}, NormSuperficie: {b.normalized_superficie}, LivableSpace: {b.livable_space}")
                        lines.append(
                            f"                UnitsMeters: {b.units_est_meters}, UnitsVolume: {b.units_est_volume}, UnitsMerged: {b.units_est_merged}"
                        )
                        lines.append(
                            f"                Res_Primary: {b.units_res_primary}, "
                            f"Res_Empty: {b.units_res_empty}, "
                            f"Res_Total: {b.units_res}, "
                            f"Res_Pct: {res_pct:.2f}, "
                            f"Res_AdjHeight: {res_adj_height:.2f}"
                        )
                        lines.append(
                            f"                NR_Secondary: {b.units_nr_secondary}, "
                            f"NR_Empty: {b.units_nr_empty}, "
                            f"NR_STR: {b.units_nr_secondary_str}, "
                            f"NR_Students: {b.units_nr_secondary_students}, "
                            f"NR_Total: {b.units_nr}, "
                            f"NR_Pct: {nr_pct:.2f}, "
                            f"NR_AdjHeight: {nr_adj_height:.2f}, "
                            f"Has_Hotel?: {(b.has_hotel or 0):.2f}"
                        )
                        lines.append(
                            f"                Empty_Pct: {empty_pct:.2f}, Empty_AdjHeight: {empty_adj_height:.2f}, "
                            f"PopEst: {b.pop_est}"
                        )
                        lines.append(f"                Measured: {getattr(b, 'measured', False)}, Surveyed: {getattr(b, 'surveyed', False)}")

                        for addr in b.addresses:
                            lines.append(f"\n                Address: {addr.address}")
                            lines.append(f"                    STRs: {addr.strs}, Hotels: {addr.hotels}, HotelsExtras: {addr.hotels_extras}")
                            if addr.meters:
                                for m in addr.meters:
                                    lines.append(
                                        f"                    Meter: {m.id} (Comp: {m.componenti}, Consumo2024: {m.consumo_2024}, Rate: {m.rate})"
                                    )
                            else:
                                lines.append(f"                    Meters: []")

        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✅ Hierarchy exported to {path}")
