import matplotlib.pyplot as plt
from collections import defaultdict

# 50 distinct colors
COLORS = [
    (0.894, 0.102, 0.110), (0.215, 0.494, 0.721), (0.302, 0.686, 0.290),
    (0.596, 0.306, 0.639), (1.000, 0.498, 0.000), (1.000, 1.000, 0.200),
    (0.651, 0.337, 0.157), (0.969, 0.506, 0.749), (0.600, 0.600, 0.600),
    (0.745, 0.682, 0.831), (0.9, 0.7, 0.0), (0.0, 0.6, 0.5), (0.8, 0.4, 0.2),
    (0.3, 0.7, 0.9), (0.9, 0.3, 0.5), (0.5, 0.8, 0.2), (0.6, 0.3, 0.7),
    (0.2, 0.4, 0.8), (0.7, 0.5, 0.1), (0.4, 0.6, 0.3), (0.8, 0.2, 0.4),
    (0.1, 0.7, 0.6), (0.6, 0.6, 0.2), (0.3, 0.3, 0.9), (0.9, 0.5, 0.3),
    (0.5, 0.2, 0.6), (0.2, 0.9, 0.4), (0.7, 0.1, 0.8), (0.4, 0.7, 0.5),
    (0.8, 0.3, 0.2), (0.6, 0.1, 0.4), (0.3, 0.6, 0.7), (0.9, 0.2, 0.1),
    (0.1, 0.5, 0.9), (0.2, 0.8, 0.5), (0.7, 0.6, 0.2), (0.4, 0.3, 0.8),
    (0.8, 0.5, 0.7), (0.3, 0.9, 0.2), (0.6, 0.4, 0.3), (0.5, 0.1, 0.9),
    (0.2, 0.6, 0.8), (0.7, 0.2, 0.5), (0.1, 0.8, 0.7), (0.9, 0.3, 0.6),
    (0.4, 0.2, 0.6), (0.6, 0.7, 0.1), (0.3, 0.5, 0.9), (0.8, 0.1, 0.3),
    (0.2, 0.9, 0.6), (0.5, 0.8, 0.1), (0.9, 0.4, 0.2)
]

class Plotter:
    def __init__(self, buildings):
        self.buildings = buildings
        self.filtered_buildings = buildings
        self.groups = {}
        self.colors = {}

    # --- Grouping ---
    def group_by_tract(self):
        return self._group("tract")

    def group_by_island(self):
        return self._group("island")

    def group_by_sestiere(self):
        return self._group("sestiere")

    def _group(self, group_type):
        groups = defaultdict(list)
        print("Building groups...")

        for b in self.filtered_buildings:
            alias_parts = b.alias.split("-")
            
            if group_type == "tract":
                key = "-".join(alias_parts[:3])  # sm-xx-xx
            elif group_type == "island":
                key = "-".join(alias_parts[:2])  # sm-xx
            elif group_type == "sestiere":
                key = alias_parts[0]             # sm
            else:
                raise ValueError("Invalid group type")
            
            #print(f"Building alias: {b.alias}, group key: {key}")
            groups[key].append(b)

        self.groups = groups
        print(f"Total groups formed: {len(groups)}")
        self.assign_colors()
        return groups

    def assign_colors(self):
        color_count = len(COLORS)
        print("Assigning colors to groups...")
        self.colors = {}
        for i, key in enumerate(sorted(self.groups.keys())):
            color = COLORS[i % color_count]
            self.colors[key] = color
            print(f"Group '{key}' assigned color {color}")
            for b in self.groups[key]:
                b.color = color
                #print(f" --> Building {b.alias} color set to {b.color}")

    # --- Filter ---
    def filter_buildings_by_alias(self, prefix):
        self.filtered_buildings = [b for b in self.buildings if b.alias.startswith(prefix)]
        print(f"Filtered {len(self.filtered_buildings)} buildings with prefix '{prefix}'")

    # --- Plotting helpers ---
    def _prepare_group(self, group):
        print(f"Preparing group: {group}")
        if group == "tract":
            self.group_by_tract()
        elif group == "island":
            self.group_by_island()
        elif group == "sestiere":
            self.group_by_sestiere()
        else:
            raise ValueError("group must be 'tract', 'island', or 'sestiere'")

    # --- Plotting methods ---
    def plot_buildings(self, group="tract", show=True):
        self._prepare_group(group)
        fig, ax = plt.subplots(figsize=(12, 8))
        print("Plotting buildings...")
        for b in self.filtered_buildings:
            print(f"Plotting building {b.alias} with color {b.color}")
            if b.polygon:
                xs = [c.x for c in b.polygon] + [b.polygon[0].x]
                ys = [c.y for c in b.polygon] + [b.polygon[0].y]
                ax.fill(xs, ys, color=b.color, alpha=0.8, edgecolor='black', linewidth=0.5)
        ax.set_aspect('equal')
        ax.axis('off')
        if show:
            plt.show()

    def plot_snake(self, group="sestiere", show=True):
        self._prepare_group(group)
        fig, ax = plt.subplots(figsize=(12, 8))
        print("Plotting snakes...")
        for key, b_list in self.groups.items():
            print(f"Snake for group '{key}' with {len(b_list)} buildings")
            sorted_b = sorted(b_list, key=lambda b: b.alias)
            xs = [b.centroid.x for b in sorted_b]
            ys = [b.centroid.y for b in sorted_b]
            ax.plot(xs, ys, linewidth=1.5, color='black')
        ax.set_aspect('equal')
        ax.axis('off')
        if show:
            plt.show()

    def plot_buildings_and_snake(self, group="sestiere", show=True):
        self._prepare_group(group)
        fig, ax = plt.subplots(figsize=(12, 8))
        print("Plotting buildings and snakes...")
        # Draw buildings
        for b in self.filtered_buildings:
            #print(f"Plotting building {b.alias} with color {b.color}")
            if b.polygon:
                xs = [c.x for c in b.polygon] + [b.polygon[0].x]
                ys = [c.y for c in b.polygon] + [b.polygon[0].y]
                ax.fill(xs, ys, color=b.color, alpha=0.8, edgecolor='black', linewidth=0.5)
        # Draw snake
        for key, b_list in self.groups.items():
            print(f"Snake for group '{key}' with {len(b_list)} buildings")
            sorted_b = sorted(b_list, key=lambda b: b.alias)
            xs = [b.centroid.x for b in sorted_b]
            ys = [b.centroid.y for b in sorted_b]
            ax.plot(xs, ys, linewidth=1.5, color='black')
        ax.set_aspect('equal')
        ax.axis('off')
        if show:
            plt.show()
