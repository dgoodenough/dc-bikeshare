# Capital Bikeshare Station Usage Map

I built this to answer one question: why do some Capital Bikeshare stations get
pulled, and why do some never get e-bikes? The one I had in mind turned out to be
among the worst-performing in the system, so stocking it wasn't worth it. Answering
that turned into an interactive month-by-month map of every station's ridership
across the DC region, built to be lightweight and honestly just fun to scroll
through.

**26,073,877 trips, May 2020 to March 2026** (71 months), 986 docked stations plus
~1,000 dockless e-bike grid cells. Python standard library plus one Leaflet HTML
file: no pandas, no build tooling, no API keys.

![python](https://img.shields.io/badge/python-3.8%2B-blue) ![deps](https://img.shields.io/badge/dependencies-stdlib%20only-green)

## What it does

- **Shows the mode change over time.** One marker per station, sized by ride volume
  and drawn as a pie of electric (teal) vs classic (blue) trips, with orange grid
  cells for dockless e-bikes binned to ~200m. A month slider (2020-05 → 2026-03) with
  play/speed controls and arrow-key stepping, and live totals per month. The clear
  macro story is e-bikes overtaking classic. Up close you can watch stations appear
  and disappear, including a few that clearly got shifted a block during construction
  and moved back a few months later.
- **Runs on nothing, on purpose.** The whole pipeline is standard-library Python, and
  the map is a single self-contained HTML file with the data embedded. No
  dependencies to install, no server, no keys. It opens in any browser and should
  still run years from now. Lightweight-and-fun-to-scroll drove every choice.
- **Reproducible from the raw source.** Three steps: download every monthly trip zip
  from the public Capital Bikeshare bucket, normalize the column variants into one
  SQLite schema, aggregate to station-months, and inline the result into the map. The
  download step is incremental, so re-running picks up new months as they publish.
  That also makes the natural next step easy: host it in my portfolio and let it
  auto-refresh.

## How it works

```
build_bikeshare_db.py   →  capitalbikeshare.db   (download + load all trips)
extract_map_data.py     →  map_data.json         (aggregate to station-months)
build_viz.py            →  bikeshare_map.html     (embed JSON into the template)
```

| File | Role |
|---|---|
| `build_bikeshare_db.py` | Downloads every monthly trip zip from the public Capital Bikeshare S3 bucket (`2020-05` → present), normalizes the column variants into one canonical schema, and loads them into a SQLite DB with derived columns (`start_date`, `start_hour`, `year_month`, `is_electric`), 10 indexes, and a `station_summary` view. Stdlib only. |
| `extract_map_data.py` | Queries the DB into a compact `map_data.json`: per-station monthly electric/classic counts, plus dockless e-bike rides grid-binned to ~200m cells. |
| `build_viz.py` | Inlines `map_data.json` into the Leaflet HTML template and writes `bikeshare_map.html`. |
| `bikeshare_explore.ipynb` | Notebook that ran the full pipeline end to end, with recorded outputs: trips per month, top stations, bike-type and member/casual splits, hour-of-day, and electric-share leaders. |

The generated data (`capitalbikeshare.db`, ~10 GB, and the `raw/` zips, ~900 MB) is
`.gitignore`d and fully reproducible:

```bash
python build_bikeshare_db.py   # ~900 MB of downloads, builds the 10 GB DB
python extract_map_data.py     # writes map_data.json
python build_viz.py            # writes bikeshare_map.html
```

`build_bikeshare_db.py` is incremental: it skips any monthly zip already present in
`raw/` and stops cleanly at the first month not yet published. The committed
`map_data.json` and `bikeshare_map.html` are snapshots through March 2026, so you can
open the map immediately without rebuilding anything.

## Data source and attribution

Trip data: [Capital Bikeshare System Data](https://capitalbikeshare.com/system-data),
published under the [Capital Bikeshare Data License Agreement](https://ride.capitalbikeshare.com/data-license-agreement).
This repository contains only derived aggregates and the code that produces them.
Basemap tiles © OpenStreetMap contributors, © CARTO.

## License

Code is [MIT](LICENSE) licensed. The underlying trip data remains subject to Capital
Bikeshare's data license linked above.
