#!/usr/bin/env python3
"""
Capital Bikeshare Data Pipeline
================================
Downloads monthly trip data from the Capital Bikeshare S3 bucket (2020-05 onward),
extracts CSVs, harmonizes schemas, and loads into a single SQLite database.

Usage:
    python build_bikeshare_db.py

Output:
    - capitalbikeshare.db   (SQLite database with all trip data + indexes)
    - raw/                  (folder with downloaded zips, kept for reference)

Requirements:
    - Python 3.8+
    - No external packages needed (uses only stdlib)
"""

import csv
import io
import os
import sqlite3
import sys
import urllib.request
import urllib.error
import zipfile
from datetime import datetime, date
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

S3_BASE = "https://s3.amazonaws.com/capitalbikeshare-data/"
START_YEAR = 2020
START_MONTH = 5
DB_NAME = "capitalbikeshare.db"
RAW_DIR = "raw"
BATCH_SIZE = 50_000  # rows per INSERT batch

# The canonical schema we normalize everything into
CANONICAL_COLUMNS = [
    "ride_id",
    "rideable_type",
    "started_at",
    "ended_at",
    "start_station_name",
    "start_station_id",
    "end_station_name",
    "end_station_id",
    "start_lat",
    "start_lng",
    "end_lat",
    "end_lng",
    "member_casual",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def generate_file_urls():
    """Generate (year, month, url) tuples for every expected monthly file."""
    today = date.today()
    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (today.year, today.month):
        filename = f"{year}{month:02d}-capitalbikeshare-tripdata.zip"
        url = S3_BASE + filename
        yield year, month, url, filename
        month += 1
        if month > 12:
            month = 1
            year += 1


def download_file(url, dest_path):
    """Download a file with progress indication. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BikeShareDataPipeline/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total else None

            with open(dest_path, "wb") as f:
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 256)  # 256KB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        mb = downloaded / 1024 / 1024
                        print(f"\r    {mb:.1f} MB ({pct:.0f}%)", end="", flush=True)
                    else:
                        mb = downloaded / 1024 / 1024
                        print(f"\r    {mb:.1f} MB", end="", flush=True)
                print()
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False  # file doesn't exist yet (future month)
        raise
    except urllib.error.URLError as e:
        print(f"\n    Network error: {e}")
        return False


def normalize_row(header_map, raw_row):
    """
    Map a raw CSV row (dict) to our canonical schema.
    Handles both the modern schema and minor column name variations.
    """
    row = {}
    for canon_col in CANONICAL_COLUMNS:
        # Try exact match first, then case-insensitive, then known aliases
        val = raw_row.get(canon_col)
        if val is None:
            # try case-insensitive
            for k, v in raw_row.items():
                if k.strip().lower() == canon_col.lower():
                    val = v
                    break
        if val is None:
            val = ""
        row[canon_col] = val.strip() if isinstance(val, str) else val
    return row


def extract_and_iterate_csv(zip_path):
    """
    Open a zip file and yield normalized row dicts from each CSV inside.
    Handles zips containing one or multiple CSVs.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            print(f"    WARNING: No CSV files found in {zip_path}")
            return

        for csv_name in csv_names:
            with zf.open(csv_name) as raw:
                # Wrap in TextIOWrapper for csv.DictReader
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
                reader = csv.DictReader(text)

                # Build a header mapping once
                header_map = {col.strip(): col.strip() for col in (reader.fieldnames or [])}

                for raw_row in reader:
                    yield normalize_row(header_map, raw_row)


# ── Main pipeline ──────────────────────────────────────────────────────────────

def main():
    # In a notebook __file__ isn't defined, so fall back to cwd
    try:
        script_dir = Path(__file__).parent.resolve()
    except NameError:
        script_dir = Path.cwd()
    os.chdir(script_dir)

    raw_dir = Path(RAW_DIR)
    raw_dir.mkdir(exist_ok=True)

    db_path = Path(DB_NAME)

    # ── 1. Download phase ──────────────────────────────────────────────────
    print("=" * 60)
    print("CAPITAL BIKESHARE DATA PIPELINE")
    print("=" * 60)
    print(f"\nDownloading monthly files from {START_YEAR}-{START_MONTH:02d} to present...\n")

    downloaded_files = []
    for year, month, url, filename in generate_file_urls():
        dest = raw_dir / filename
        label = f"{year}-{month:02d}"

        if dest.exists() and dest.stat().st_size > 0:
            print(f"  [{label}] Already downloaded, skipping.")
            downloaded_files.append((year, month, dest))
            continue

        print(f"  [{label}] Downloading {filename}...")
        if download_file(url, dest):
            downloaded_files.append((year, month, dest))
        else:
            print(f"  [{label}] Not available (probably not published yet). Stopping.")
            break

    print(f"\n  Total files: {len(downloaded_files)}")

    if not downloaded_files:
        print("\nNo files downloaded. Check your internet connection and try again.")
        sys.exit(1)

    # ── 2. Database creation ───────────────────────────────────────────────
    print(f"\nBuilding SQLite database: {db_path.name}")
    print("-" * 60)

    # Remove old DB to rebuild from scratch
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-256000")  # 256MB cache

    # Create the trips table
    conn.execute("""
        CREATE TABLE trips (
            ride_id          TEXT,
            rideable_type    TEXT,
            started_at       TEXT,
            ended_at         TEXT,
            start_station_name TEXT,
            start_station_id   TEXT,
            end_station_name   TEXT,
            end_station_id     TEXT,
            start_lat        REAL,
            start_lng        REAL,
            end_lat          REAL,
            end_lng          REAL,
            member_casual    TEXT,
            -- Derived columns for easier querying
            start_date       TEXT,
            start_hour       INTEGER,
            year_month       TEXT,
            is_electric      INTEGER  -- 1 = electric, 0 = classic/docked
        )
    """)

    # ── 3. Load phase ──────────────────────────────────────────────────────
    total_rows = 0
    insert_sql = """
        INSERT INTO trips VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """

    for year, month, zip_path in downloaded_files:
        label = f"{year}-{month:02d}"
        print(f"  Loading [{label}]...", end=" ", flush=True)
        month_rows = 0
        batch = []

        for row in extract_and_iterate_csv(zip_path):
            # Parse derived columns
            started_at = row["started_at"]
            start_date = ""
            start_hour = None
            year_month = f"{year}-{month:02d}"

            if started_at:
                try:
                    # Try common formats
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f",
                                "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S"):
                        try:
                            dt = datetime.strptime(started_at, fmt)
                            start_date = dt.strftime("%Y-%m-%d")
                            start_hour = dt.hour
                            year_month = dt.strftime("%Y-%m")
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

            # Convert lat/lng to float
            def to_float(v):
                try:
                    return float(v) if v else None
                except (ValueError, TypeError):
                    return None

            # Classify bike type: electric vs classic/docked
            rtype = (row["rideable_type"] or "").lower()
            is_electric = 1 if "electric" in rtype else 0

            values = (
                row["ride_id"],
                row["rideable_type"],
                row["started_at"],
                row["ended_at"],
                row["start_station_name"],
                row["start_station_id"],
                row["end_station_name"],
                row["end_station_id"],
                to_float(row["start_lat"]),
                to_float(row["start_lng"]),
                to_float(row["end_lat"]),
                to_float(row["end_lng"]),
                row["member_casual"],
                start_date,
                start_hour,
                year_month,
                is_electric,
            )
            batch.append(values)
            month_rows += 1

            if len(batch) >= BATCH_SIZE:
                conn.executemany(insert_sql, batch)
                batch.clear()

        # Flush remaining
        if batch:
            conn.executemany(insert_sql, batch)
            batch.clear()

        conn.commit()
        total_rows += month_rows
        print(f"{month_rows:>10,} rows  (running total: {total_rows:,})")

    # ── 4. Create indexes for visualization queries ────────────────────────
    print(f"\nCreating indexes for fast querying...")

    indexes = [
        ("idx_year_month",       "trips(year_month)"),
        ("idx_start_date",       "trips(start_date)"),
        ("idx_start_station",    "trips(start_station_name)"),
        ("idx_end_station",      "trips(end_station_name)"),
        ("idx_start_station_id", "trips(start_station_id)"),
        ("idx_member_casual",    "trips(member_casual)"),
        ("idx_rideable_type",    "trips(rideable_type)"),
        ("idx_start_hour",       "trips(start_hour)"),
        ("idx_is_electric",      "trips(is_electric)"),
        ("idx_station_month",    "trips(start_station_name, year_month)"),
    ]
    for idx_name, idx_def in indexes:
        print(f"  Creating {idx_name}...")
        conn.execute(f"CREATE INDEX {idx_name} ON {idx_def}")
    conn.commit()

    # ── 5. Create a stations summary view ──────────────────────────────────
    print("Creating stations summary view...")
    conn.execute("""
        CREATE VIEW station_summary AS
        SELECT
            start_station_name AS station_name,
            start_station_id   AS station_id,
            ROUND(AVG(start_lat), 6) AS lat,
            ROUND(AVG(start_lng), 6) AS lng,
            COUNT(*) AS total_departures,
            SUM(CASE WHEN member_casual = 'member' THEN 1 ELSE 0 END) AS member_departures,
            SUM(CASE WHEN member_casual = 'casual' THEN 1 ELSE 0 END) AS casual_departures,
            SUM(CASE WHEN is_electric = 1 THEN 1 ELSE 0 END) AS electric_departures,
            SUM(CASE WHEN is_electric = 0 THEN 1 ELSE 0 END) AS classic_departures,
            MIN(start_date) AS first_seen,
            MAX(start_date) AS last_seen
        FROM trips
        WHERE start_station_name != ''
        GROUP BY start_station_name
    """)
    conn.commit()

    # ── 6. Summary stats ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)

    row_count = conn.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
    station_count = conn.execute("SELECT COUNT(*) FROM station_summary").fetchone()[0]
    date_range = conn.execute(
        "SELECT MIN(start_date), MAX(start_date) FROM trips WHERE start_date != ''"
    ).fetchone()
    db_size_mb = db_path.stat().st_size / 1024 / 1024

    print(f"\n  Database:     {db_path.name} ({db_size_mb:.1f} MB)")
    print(f"  Total trips:  {row_count:,}")
    print(f"  Stations:     {station_count:,}")
    print(f"  Date range:   {date_range[0]} to {date_range[1]}")
    print(f"\n  Raw zips kept in: {raw_dir}/")

    # Quick sample queries to verify
    print("\n  Sample queries you can run:")
    print('    sqlite3 capitalbikeshare.db "SELECT * FROM station_summary ORDER BY total_departures DESC LIMIT 10;"')
    print('    sqlite3 capitalbikeshare.db "SELECT year_month, COUNT(*) as trips FROM trips GROUP BY year_month ORDER BY year_month;"')
    print('    sqlite3 capitalbikeshare.db "SELECT rideable_type, COUNT(*) FROM trips GROUP BY rideable_type;"')

    conn.close()
    print("\nAll done! The database is ready for your visualizations.\n")


if __name__ == "__main__":
    main()
