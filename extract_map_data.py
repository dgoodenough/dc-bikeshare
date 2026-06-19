"""
Extract station-level monthly data for the interactive map visualization.
Run this locally — it queries the SQLite DB and writes a compact JSON file.

Usage (in notebook or terminal):
    %run extract_map_data.py
    # or: python extract_map_data.py
"""

import sqlite3
import json
from pathlib import Path

OUTPUT = "map_data.json"

db = sqlite3.connect("capitalbikeshare.db")
db.row_factory = sqlite3.Row

print("Querying all station monthly data (this may take a few minutes)...")

# 1. Station monthly data — no geographic filter
station_monthly = db.execute("""
    SELECT
        start_station_name AS name,
        ROUND(AVG(start_lat), 6) AS lat,
        ROUND(AVG(start_lng), 6) AS lng,
        year_month,
        SUM(CASE WHEN is_electric = 1 THEN 1 ELSE 0 END) AS electric,
        SUM(CASE WHEN is_electric = 0 THEN 1 ELSE 0 END) AS classic
    FROM trips
    WHERE start_station_name != ''
      AND start_lat IS NOT NULL
    GROUP BY start_station_name, year_month
    ORDER BY start_station_name, year_month
""").fetchall()

print(f"  Station-month rows: {len(station_monthly)}")

# Organize into {station_name: {lat, lng, months: {ym: {e, c}}}}
stations = {}
for r in station_monthly:
    name = r["name"]
    if name not in stations:
        stations[name] = {"lat": r["lat"], "lng": r["lng"], "months": {}}
    stations[name]["months"][r["year_month"]] = {
        "e": r["electric"],
        "c": r["classic"]
    }

print(f"  Unique stations: {len(stations)}")

# 2. Dockless rides: grid-aggregate into ~0.002 degree cells (~200m)
#    These are rides with no station name but valid lat/lng
print("Querying dockless e-bike rides (may also take a few minutes)...")

GRID = 0.002  # ~200m cells

dockless_monthly = db.execute("""
    SELECT
        ROUND(start_lat / {grid}, 0) * {grid} AS glat,
        ROUND(start_lng / {grid}, 0) * {grid} AS glng,
        year_month,
        COUNT(*) AS cnt
    FROM trips
    WHERE (start_station_name = '' OR start_station_name IS NULL)
      AND start_lat IS NOT NULL
      AND is_electric = 1
    GROUP BY glat, glng, year_month
""".format(grid=GRID)).fetchall()

print(f"  Dockless grid-month rows: {len(dockless_monthly)}")

# Organize into grid cells
dockless = {}
for r in dockless_monthly:
    key = f"{r['glat']:.3f},{r['glng']:.3f}"
    if key not in dockless:
        dockless[key] = {"lat": r["glat"], "lng": r["glng"], "months": {}}
    dockless[key]["months"][r["year_month"]] = r["cnt"]

print(f"  Unique grid cells: {len(dockless)}")

# 3. Get all months
months = [r[0] for r in db.execute(
    "SELECT DISTINCT year_month FROM trips ORDER BY year_month"
).fetchall()]

print(f"  Months: {months[0]} to {months[-1]} ({len(months)} total)")

db.close()

# 4. Write JSON
output = {
    "months": months,
    "stations": stations,
    "dockless": dockless
}

out_path = Path(OUTPUT)
with open(out_path, "w") as f:
    json.dump(output, f, separators=(",", ":"))

size_mb = out_path.stat().st_size / 1024 / 1024
print(f"\nWrote {OUTPUT} ({size_mb:.1f} MB)")
print("You're ready to build the viz!")
