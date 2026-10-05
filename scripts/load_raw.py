#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EL-Schritt fuer das dbt-Projekt `airbnb_analytics`.

Liest die Inside-Airbnb-Rohdaten (mehrere Snapshots je Stadt) und schreibt sie
in das lokale DuckDB-Warehouse (Schema `raw`). dbt uebernimmt danach das T.

Erzeugte Tabellen:
  raw.listings_all    alle Listings aller Snapshots, vereinheitlichtes Schema
  raw.neighbourhoods  Stadtteil-Zuordnung je Stadt
  raw.load_log        Audit-Tabelle (Quelle, Zeilen, Ladezeitpunkt)

Aufruf:
  python3 scripts/load_raw.py [--raw-dir PFAD] [--db PFAD]

Standardpfade lassen sich per Umgebungsvariable setzen:
  AIRBNB_RAW_DIR, AIRBNB_DUCKDB
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import date
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[1]

DEFAULT_RAW_DIR = os.environ.get("AIRBNB_RAW_DIR", str(REPO.parent / "airbnb" / "raw"))
DEFAULT_DB = os.environ.get("AIRBNB_DUCKDB", str(REPO / "data" / "airbnb.duckdb"))

# Zielfeld -> SQL-Ausdruck auf Basis der Rohspalten.
# Fehlt eine Rohspalte in einem Snapshot, wird NULL eingesetzt (Schema-Drift).
COLUMN_EXPRESSIONS: dict[str, str] = {
    "listing_id": 'TRY_CAST("id" AS BIGINT)',
    "listing_name": 'CAST("name" AS VARCHAR)',
    "host_id": 'TRY_CAST("host_id" AS BIGINT)',
    "host_name": 'CAST("host_name" AS VARCHAR)',
    "district": "NULLIF(TRIM(CAST(\"neighbourhood_group\" AS VARCHAR)), '')",
    "subdistrict": "NULLIF(TRIM(CAST(\"neighbourhood\" AS VARCHAR)), '')",
    "latitude": 'TRY_CAST("latitude" AS DOUBLE)',
    "longitude": 'TRY_CAST("longitude" AS DOUBLE)',
    "room_type": "NULLIF(TRIM(CAST(\"room_type\" AS VARCHAR)), '')",
    "price_eur": (
        "TRY_CAST(REPLACE(REGEXP_REPLACE(CAST(\"price\" AS VARCHAR), '[^0-9.,]', '', 'g'), "
        "',', '') AS DOUBLE)"
    ),
    "min_nights": 'TRY_CAST("minimum_nights" AS BIGINT)',
    "review_count": 'TRY_CAST("number_of_reviews" AS BIGINT)',
    "last_review_date": 'TRY_CAST("last_review" AS DATE)',
    "reviews_per_month": 'TRY_CAST("reviews_per_month" AS DOUBLE)',
    "host_listings_count": 'TRY_CAST("calculated_host_listings_count" AS BIGINT)',
    "availability_365": 'TRY_CAST("availability_365" AS BIGINT)',
    "reviews_ltm": 'TRY_CAST("number_of_reviews_ltm" AS BIGINT)',
    "license": "NULLIF(TRIM(CAST(\"license\" AS VARCHAR)), '')",
}

# Zieltyp fuer Spalten, die in einzelnen Snapshots fehlen (Schema-Drift).
# Ohne expliziten Typ wuerde CAST(NULL AS VARCHAR) die Spalte im UNION
# auf VARCHAR zwingen, z. B. reviews_ltm im historischen Snapshot 2015-09.
NULL_TYPES: dict[str, str] = {
    "listing_id": "BIGINT",
    "listing_name": "VARCHAR",
    "host_id": "BIGINT",
    "host_name": "VARCHAR",
    "district": "VARCHAR",
    "subdistrict": "VARCHAR",
    "latitude": "DOUBLE",
    "longitude": "DOUBLE",
    "room_type": "VARCHAR",
    "price_eur": "DOUBLE",
    "min_nights": "BIGINT",
    "review_count": "BIGINT",
    "last_review_date": "DATE",
    "reviews_per_month": "DOUBLE",
    "host_listings_count": "BIGINT",
    "availability_365": "BIGINT",
    "reviews_ltm": "BIGINT",
    "license": "VARCHAR",
}

# Historische Snapshots (aeltere Mirrors mit abweichendem Schema).
# Quelle: Inside Airbnb, historische Stadt-Daten.
#   Berlin  2015-09: hist/berlin-github-listings.csv
#   Muenchen 2020-05: hist/unzipped/listings.csv (Bezirke nur in
#                     neighbourhood_cleansed, kein neighbourhood_group)
# overrides: Ziel-Spalte -> abweichende Quellspalte in genau dieser Datei.
HIST_SNAPSHOTS = [
    ("Berlin", date(2015, 9, 1), "hist/berlin-github-listings.csv", {}),
    (
        "Muenchen",
        date(2020, 5, 24),
        "hist/unzipped/listings.csv",
        {"subdistrict": "neighbourhood_cleansed"},
    ),
]

CITY_DIRS = {"berlin": "Berlin", "munich": "Muenchen"}


def discover_snapshots(raw_dir: Path) -> list[tuple[str, date, Path, dict]]:
    """Findet alle Snapshot-Dateien: raw/vis/<stadt>-<datum>-listings.csv."""
    found: list[tuple[str, date, Path, dict]] = []
    vis = raw_dir / "vis"
    if vis.is_dir():
        pattern = re.compile(r"^(berlin|munich)-(\d{4}-\d{2}-\d{2})-listings\.csv$")
        for path in sorted(vis.glob("*.csv")):
            m = pattern.match(path.name)
            if m:
                found.append((CITY_DIRS[m.group(1)], date.fromisoformat(m.group(2)), path, {}))
    for city, snap, rel, overrides in HIST_SNAPSHOTS:
        path = raw_dir / rel
        if path.is_file():
            found.append((city, snap, path, overrides))
    return found


def columns_of(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    rows = con.execute(
        "SELECT * FROM read_csv_auto(?) LIMIT 0", [str(path)]
    ).description
    return [r[0] for r in rows]


def build_union(con: duckdb.DuckDBPyConnection, snapshots) -> str:
    selects = []
    for city, snap, path, overrides in snapshots:
        present = {c.lower() for c in columns_of(con, path)}
        exprs = []
        for target, expr in COLUMN_EXPRESSIONS.items():
            source_col = re.search(r'"([^"]+)"', expr)
            name = source_col.group(1) if source_col else None
            override = overrides.get(target)
            if override:
                # Abweichende Quellspalte in diesem Snapshot (z. B. historisches Schema).
                expr = expr.replace(f'"{name}"', f'"{override}"')
                name = override
            if name and name.lower() not in present:
                exprs.append(f"CAST(NULL AS {NULL_TYPES[target]}) AS {target}")
            else:
                exprs.append(f"{expr} AS {target}")
        selects.append(
            "SELECT\n"
            f"        '{city}' AS city,\n"
            f"        DATE '{snap.isoformat()}' AS snapshot_date,\n"
            f"        '{path.name}' AS source_file,\n"
            "        " + ",\n        ".join(exprs) + "\n"
            f"      FROM read_csv_auto('{path}', header = true)"
        )
    return "\n    UNION ALL BY NAME\n    ".join(selects)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    raw_dir, db_path = Path(args.raw_dir), Path(args.db)
    if not raw_dir.is_dir():
        raise SystemExit(f"Rohdatenverzeichnis nicht gefunden: {raw_dir}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    snapshots = discover_snapshots(raw_dir)
    if not snapshots:
        raise SystemExit(f"Keine Snapshot-Dateien unter {raw_dir}/vis gefunden.")

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    con.execute(
        "CREATE OR REPLACE TABLE raw.listings_all AS\n"
        "    SELECT * FROM (\n    " + build_union(con, snapshots) + "\n    ) AS alle\n"
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE raw.neighbourhoods AS
        SELECT 'Berlin' AS city, neighbourhood_group AS district, neighbourhood AS subdistrict
        FROM read_csv_auto(?, header = true)
        WHERE neighbourhood IS NOT NULL AND TRIM(neighbourhood) <> ''
        UNION ALL
        SELECT 'Muenchen', neighbourhood_group, neighbourhood
        FROM read_csv_auto(?, header = true)
        WHERE neighbourhood IS NOT NULL AND TRIM(neighbourhood) <> ''
        """,
        [str(raw_dir / "berlin" / "neighbourhoods.csv"),
         str(raw_dir / "munich" / "neighbourhoods.csv")],
    )

    con.execute("DROP TABLE IF EXISTS raw.load_log")
    con.execute(
        """
        CREATE TABLE raw.load_log AS
        SELECT source_file, city, snapshot_date, COUNT(*) AS row_count,
               MIN(loaded_at) AS loaded_at
        FROM (
            SELECT *, CURRENT_TIMESTAMP AS loaded_at FROM raw.listings_all
        )
        GROUP BY ALL
        ORDER BY city, snapshot_date
        """
    )

    print(f"Warehouse: {db_path}")
    print(f"Snapshots geladen: {len(snapshots)}")
    for row in con.execute(
        "SELECT city, snapshot_date, source_file, row_count FROM raw.load_log ORDER BY city, snapshot_date"
    ).fetchall():
        print("  {:<9} {}  {:<42} {:>7} Zeilen".format(*[str(v) for v in row]))
    con.close()


if __name__ == "__main__":
    main()
