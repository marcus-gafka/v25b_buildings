# printer.py
from typing import Union

def verbose(obj):
    """Pretty summary of the full hierarchy — works for Dataset, Sestiere, Island, or Tract."""
    from dataset import Dataset, Sestiere, Island, Tract, Building

    def sestieri_iterable(sestieri):
        """Return an iterable over Sestiere objects, whether it's a dict or a list."""
        if isinstance(sestieri, dict):
            return sestieri.values()
        return sestieri

    if isinstance(obj, Dataset):
        print(f"\n📂 Dataset Summary ({len(obj.features)} features loaded from {obj.source})")
        print("=" * 100)
        s_list = sestieri_iterable(obj.sestieri)
        total_islands = sum(len(s.islands) for s in s_list)
        total_tracts = sum(len(i.tracts) for s in s_list for i in s.islands)
        total_buildings = sum(len(t.buildings) for s in s_list for i in s.islands for t in i.tracts)

        print(f"🏙️  Sestieri:  {len(list(s_list))}")
        print(f"🏝️  Islands:   {total_islands}")
        print(f"📏  Tracts:    {total_tracts}")
        print(f"🏠  Buildings: {total_buildings}")
        print("=" * 100)

        for s in sestieri_iterable(obj.sestieri):
            verbose(s)
        print("\n✅ Hierarchy summary complete.\n")

    elif isinstance(obj, Sestiere):
        print(f"\n🟦 Sestiere {obj.code} — {len(obj.islands)} islands")
        print("-" * 60)
        for i in obj.islands:
            verbose(i)
        print("-" * 60)

    elif isinstance(obj, Island):
        print(f"  🏝️  Island {obj.code}: {len(obj.tracts)} tracts")
        for t in obj.tracts:
            verbose(t)

    elif isinstance(obj, Tract):
        print(f"     ├─ Tract {obj.id} ({len(obj.buildings)} buildings)")
        for b in obj.buildings:
            print(f"     │    • prog: {b.prog}")
        print("     │")

    else:
        print("⚠️ Unknown object type passed to verbose()")


def summary(obj):
    from dataset import Dataset, Sestiere, Island, Tract, Building

    def sestieri_iterable(sestieri):
        if isinstance(sestieri, dict):
            return sestieri.values()
        return sestieri

    if isinstance(obj, Dataset):
        print(f"\n📊 Sestiere Overview ({len(list(sestieri_iterable(obj.sestieri)))} total):")
        print("=" * 100)
        for s in sestieri_iterable(obj.sestieri):
            summary(s)
        print("=" * 100)

    elif isinstance(obj, Sestiere):
        num_islands = len(obj.islands)
        num_tracts = sum(len(i.tracts) for i in obj.islands)
        num_buildings = sum(len(t.buildings) for i in obj.islands for t in i.tracts)
        island_codes = ", ".join(i.code for i in obj.islands) if obj.islands else "None"

        print(f"{obj.name} ({obj.code}) — {num_islands} Islands, {num_tracts} Tracts, {num_buildings} Buildings")
        print(f"  ↳ Islands: {island_codes}\n")

    elif isinstance(obj, Island):
        num_tracts = len(obj.tracts)
        num_buildings = sum(len(t.buildings) for t in obj.tracts)
        print(f"Island {obj.code} — {num_tracts} Tracts, {num_buildings} Buildings")

    elif isinstance(obj, Tract):
        print(f"Tract {obj.id} — {len(obj.buildings)} Buildings")

    else:
        print("⚠️ Unknown object type passed to summary()")
