# Capital Bikeshare — Station Usage Map

A small, dependency-free pipeline that turns every Capital Bikeshare trip
(Washington, DC region) into an interactive month-by-month map of station
ridership. Built entirely on the Python standard library plus a single
Leaflet HTML file — no pandas, no build tooling, no API keys.

**Coverage:** 26,073,877 trips, May 2020 → March 2026 (71 months), 986 docked
stations + ~1,000 dockless e-bike grid cells.

![pipeline](https://img.shields.io/badge/python-3.8%2B-blue) ![deps](https://img.shields.io/badge/dependencies-stdlib%20only-green)

## The map

`bikeshare_map.html` is a self-contained interactive visualization (Leaflet +
CARTO dark basemap, all data embedded — just open it in a browser):

- One marker per station, sized by ride volume, drawn as a pie of
  **electric** (teal) vs **classic** (blue) trips.
- Orange circles for **dockless** e-bike trips, aggregated into ~200 m grid cells.
- A **month slider** (2020-05 → 2026-03) with Play / speed controls and
  arrow-key stepping; live totals update per month.

## How it works

```
build_bikeshare_db.py   →  capitalbikeshare.db   (download + load all trips)
extract_map_data.py     →  map_data.json         (aggregate to station-months)
build_viz.py            →  bikeshare_map.html     (embed JSON into the template)
```

| File | Role |
|---|---|
| `build_bikeshare_db.py` | Downloads every monthly trip zip from the public Capital Bikeshare S3 bucket (`2020-05` → present), normalizes the column variants into one canonical schema, and loads them into a SQLite DB with derived columns (`start_date`, `start_hour`, `year_month`, `is_electric`), 10 indexes, and a `station_summary` view. Stdlib only. |
| `extract_map_data.py` | Queries the DB into a compact `map_data.json`: per-station monthly electric/classic counts, plus dockless e-bike rides grid-binned to ~200 m cells. |
| `build_viz.py` | Inlines `map_data.json` into the Leaflet HTML template and writes `bikeshare_map.html`. |
| `bikeshare_explore.ipynb` | Notebook that ran the full pipeline end to end, with recorded outputs — trips per month, top stations, bike-type and member/casual splits, hour-of-day, and electric-share leaders. |

### Data schema

The `trips` table mirrors Capital Bikeshare's modern CSV columns
(`ride_id`, `rideable_type`, `started_at`, `ended_at`, start/end station
name+id, start/end lat+lng, `member_casual`) and adds four derived columns:

| column | meaning |
|---|---|
| `start_date` | `YYYY-MM-DD` parsed from `started_at` |
| `start_hour` | hour of day, 0–23 |
| `year_month` | `YYYY-MM` bucket used by the map slider |
| `is_electric` | `1` if `rideable_type` contains "electric", else `0` |

## Regenerating from scratch

The generated data (`capitalbikeshare.db`, ~10 GB, and the `raw/` zips,
~900 MB) is **not** committed — it's `.gitignore`d and fully reproducible:

```bash
python build_bikeshare_db.py   # ~900 MB of downloads, builds the 10 GB DB
python extract_map_data.py     # writes map_data.json
python build_viz.py            # writes bikeshare_map.html
```

`build_bikeshare_db.py` is incremental: it skips any monthly zip already
present in `raw/`, and stops cleanly when it hits a month not yet published.
Re-running it picks up new months as Capital Bikeshare releases them.

The committed `map_data.json` and `bikeshare_map.html` are snapshots through
March 2026, so you can open the map immediately without rebuilding anything.

## Data source & attribution

Trip data: [Capital Bikeshare System Data](https://capitalbikeshare.com/system-data),
published under the [Capital Bikeshare Data License Agreement](https://ride.capitalbikeshare.com/data-license-agreement).
This repository contains only derived aggregates and the code that produces
them. Basemap tiles © OpenStreetMap contributors, © CARTO.

## License

Code is MIT licensed — see [LICENSE](LICENSE). The underlying trip data
remains subject to Capital Bikeshare's data license linked above.
