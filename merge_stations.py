"""
Merge station records that are really one physical station.

Capital Bikeshare renames stations ("Lee Hwy" -> "Langston Blvd"), fixes typos, and
sometimes pulls a dock for a few months of construction before putting it back under a
slightly different name. Each name becomes its own station in map_data.json, which
splits one dock's history across several markers.

Two stations are merged when they sit within MAX_DISTANCE_M of each other and are
essentially never active in the same month (at most MAX_OVERLAP_MONTHS, which covers
the month a rename happens), with no more than MAX_GAP_MONTHS between one going quiet
and the other starting. Two docks that really coexist side by side are active together
for years, so they never meet the overlap rule. A temporary relocation a block or more
away is left alone.

The merged station takes the name and location of the most recently active record.

Usage:
    python merge_stations.py          # merge in place in map_data.json
    (also called by extract_map_data.py, so rebuilds keep the merges)
"""

import json
import math
import sys

MAX_DISTANCE_M = 30
MAX_OVERLAP_MONTHS = 2
MAX_GAP_MONTHS = 12


def _distance_m(a, b):
    dy = (a["lat"] - b["lat"]) * 111_320
    dx = (a["lng"] - b["lng"]) * 111_320 * math.cos(math.radians((a["lat"] + b["lat"]) / 2))
    return math.hypot(dx, dy)


def merge_stations(stations, months):
    """Merge in place. Returns a list of (kept_name, [absorbed names]) groups."""
    month_idx = {m: i for i, m in enumerate(months)}

    def active(info):
        return sorted(month_idx[m] for m, v in info["months"].items() if v["e"] + v["c"] > 0)

    names = [n for n in stations if active(stations[n])]
    act = {n: active(stations[n]) for n in names}

    parent = {n: n for n in names}

    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if _distance_m(stations[a], stations[b]) > MAX_DISTANCE_M:
                continue
            A, B = act[a], act[b]
            if len(set(A) & set(B)) > MAX_OVERLAP_MONTHS:
                continue
            first, second = (A, B) if A[0] <= B[0] else (B, A)
            if second[0] - first[-1] - 1 > MAX_GAP_MONTHS:
                continue
            parent[find(a)] = find(b)

    groups = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)

    merged = []
    for members in groups.values():
        if len(members) == 1:
            continue
        total = lambda n: sum(v["e"] + v["c"] for v in stations[n]["months"].values())
        keep = max(members, key=lambda n: (act[n][-1], total(n)))
        combined = {}
        for n in members:
            for ym, v in stations[n]["months"].items():
                cur = combined.setdefault(ym, {"e": 0, "c": 0})
                cur["e"] += v["e"]
                cur["c"] += v["c"]
        info = stations[keep]
        info["months"] = {ym: combined[ym] for ym in sorted(combined)}
        absorbed = sorted((n for n in members if n != keep), key=lambda n: act[n][0])
        for n in absorbed:
            del stations[n]
        merged.append((keep, absorbed))

    merged.sort(key=lambda g: g[0])
    return merged


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "map_data.json"
    with open(path) as f:
        data = json.load(f)
    before = len(data["stations"])
    groups = merge_stations(data["stations"], data["months"])
    for keep, absorbed in groups:
        print(f"  {keep}  <-  {' | '.join(absorbed)}")
    print(f"Merged {sum(len(a) for _, a in groups)} records into {len(groups)} stations "
          f"({before} -> {len(data['stations'])})")
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
