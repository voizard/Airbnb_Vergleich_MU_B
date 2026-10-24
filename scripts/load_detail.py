#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EL-Schritt fuer die Detail-Snapshots von Inside Airbnb.

Warum eine zweite Quelle: `raw.listings_all` stammt aus
`visualisations/listings.csv` (19 Spalten). Diese Datei enthaelt **keine**
Auslastung. `estimated_occupancy_l365d` und `estimated_revenue_l365d` stehen nur
in der detaillierten `data/listings.csv.gz` (85-90 Spalten) — ohne sie ist keine
Auslastungsseite moeglich. Zusaetzlich liefert die Detaildatei Groesse
(`accommodates`, `bedrooms`, `beds`), `host_is_superhost`, `review_scores_rating`
und `property_type`.

Beziehung der beiden Quellen (verifiziert 2026-10-24, Juni-Stand):
  Detail ist eine echte Teilmenge der visualisations-Datei.
  Berlin   12.776 (Detail) von 12.855 (vis) — 79 Listings nur in vis
  Muenchen  6.865 (Detail) von  6.890 (vis) — 25 Listings nur in vis
  Kein Listing existiert nur im Detail. Die Differenz sind ausschliesslich
  `Private room`-Eintraege ohne Lizenz (Hotel-/Hostelzimmer-Inventar).

Zeitraum der Auslastungs- und Umsatzwerte (wichtig fuer jeden Untertitel):
  `estimated_occupancy_l365d` und `estimated_revenue_l365d` sind **rollierende
  365-Tage-Werte**, kein Kalenderjahr und kein Monat. Ein Feld "Zeitraum von/bis"
  gibt es in der Datei nicht - die Bedeutung steckt nur im Spaltennamen (`l365d`).
  Anker ist `last_scraped`, und der variiert **innerhalb einer Datei**:
    Berlin   "2026-06-26": 26.06. (34 Zeilen), 27.06. (6.624), 03.07. (6.118)
    Muenchen "2026-06-29": 29.06. (4.399), 02.07. (2.466)
  Das Fenster ist je Inserat [last_scraped - 365 Tage, last_scraped], fuer den
  Juni-Stand also grob 27.06.2025 - 03.07.2026. Der Verzeichnisname ist das
  Veroeffentlichungsdatum, nicht der Scrape-Tag.
  Zusatzfalle: der Preis im Umsatz ist der Preis **am Scrape-Tag**, nicht der
  realisierte Preis der Naechte. Das Volumen ist daher "Preis heute x gebuchte
  Naechte der letzten 365 Tage" - ein Hybrid, kein realisierter Umsatz.
  Deshalb wird `last_scraped` mitgeladen: ohne die Spalte ist der Zeitraum im
  Warehouse nicht belegbar.

Erzeugte Tabelle:
  raw.listings_detail   eine Zeile je Listing, Stadt und Detail-Snapshot
  raw.load_log_detail   Audit-Tabelle (Quelle, Zeilen, Scrape-Spanne, Ladezeitpunkt)

Aufruf:
  python3 scripts/load_detail.py [--raw-dir PFAD] [--db PFAD]

Standardpfade per Umgebungsvariable: AIRBNB_RAW_DIR, AIRBNB_DUCKDB
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

# Zielfeld -> SQL-Ausdruck auf den Rohspalten der Detaildatei.
COLUMN_EXPRESSIONS: dict[str, str] = {
    "listing_id": 'TRY_CAST("id" AS BIGINT)',
    "listing_name": 'CAST("name" AS VARCHAR)',
    "host_id": 'TRY_CAST("host_id" AS BIGINT)',
    "host_name": 'CAST("host_name" AS VARCHAR)',
    "host_is_superhost": 'LOWER(CAST("host_is_superhost" AS VARCHAR)) = \'t\'',
    # Detaildatei: Bezirke bereits bereinigt. Berlin liefert die 12 Bezirke in
    # neighbourhood_group_cleansed, Muenchen hat dort nichts und liefert die
    # 25 Stadtbezirke in neighbourhood_cleansed.
    "district": "NULLIF(TRIM(CAST(\"neighbourhood_group_cleansed\" AS VARCHAR)), '')",
    "subdistrict": "NULLIF(TRIM(CAST(\"neighbourhood_cleansed\" AS VARCHAR)), '')",
    "latitude": 'TRY_CAST("latitude" AS DOUBLE)',
    "longitude": 'TRY_CAST("longitude" AS DOUBLE)',
    "room_type": "NULLIF(TRIM(CAST(\"room_type\" AS VARCHAR)), '')",
    "property_type": "NULLIF(TRIM(CAST(\"property_type\" AS VARCHAR)), '')",
    "price_eur": (
        "TRY_CAST(REPLACE(REGEXP_REPLACE(CAST(\"price\" AS VARCHAR), '[^0-9.,]', '', 'g'), "
        "',', '') AS DOUBLE)"
    ),
    "min_nights": 'TRY_CAST("minimum_nights" AS BIGINT)',
    "accommodates": 'TRY_CAST("accommodates" AS BIGINT)',
    "bedrooms": 'TRY_CAST("bedrooms" AS DOUBLE)',
    "beds": 'TRY_CAST("beds" AS DOUBLE)',
    "bathrooms_text": "NULLIF(TRIM(CAST(\"bathrooms_text\" AS VARCHAR)), '')",
    "review_count": 'TRY_CAST("number_of_reviews" AS BIGINT)',
    "reviews_ltm": 'TRY_CAST("number_of_reviews_ltm" AS BIGINT)',
    "reviews_per_month": 'TRY_CAST("reviews_per_month" AS DOUBLE)',
    "review_scores_rating": 'TRY_CAST("review_scores_rating" AS DOUBLE)',
    "last_review_date": 'TRY_CAST("last_review" AS DATE)',
    "host_listings_count": 'TRY_CAST("calculated_host_listings_count" AS BIGINT)',
    "availability_365": 'TRY_CAST("availability_365" AS BIGINT)',
    "license": "NULLIF(TRIM(CAST(\"license\" AS VARCHAR)), '')",
    # Nur in der Detaildatei:
    "occupancy_l365d": 'TRY_CAST("estimated_occupancy_l365d" AS DOUBLE)',
    "revenue_l365d": 'TRY_CAST("estimated_revenue_l365d" AS DOUBLE)',
    "scrape_id": 'TRY_CAST("scrape_id" AS BIGINT)',
    # Anker des 365-Tage-Fensters von occupancy_l365d/revenue_l365d.
    "last_scraped": 'TRY_CAST("last_scraped" AS DATE)',
}

# Zieltyp fuer Spalten, die in einzelnen Snapshops fehlen (85 vs. 90 Spalten).
NULL_TYPES: dict[str, str] = {
    "listing_id": "BIGINT", "listing_name": "VARCHAR", "host_id": "BIGINT",
    "host_name": "VARCHAR", "host_is_superhost": "BOOLEAN", "district": "VARCHAR",
    "subdistrict": "VARCHAR", "latitude": "DOUBLE", "longitude": "DOUBLE",
    "room_type": "VARCHAR", "property_type": "VARCHAR", "price_eur": "DOUBLE",
    "min_nights": "BIGINT", "accommodates": "BIGINT", "bedrooms": "DOUBLE",
    "beds": "DOUBLE", "bathrooms_text": "VARCHAR", "review_count": "BIGINT",
    "reviews_ltm": "BIGINT", "reviews_per_month": "DOUBLE",
    "review_scores_rating": "DOUBLE", "last_review_date": "DATE",
    "host_listings_count": "BIGINT", "availability_365": "BIGINT",
    "license": "VARCHAR", "occupancy_l365d": "DOUBLE", "revenue_l365d": "DOUBLE",
    "scrape_id": "BIGINT", "last_scraped": "DATE",
}

CITY_DIRS = {"berlin": "Berlin", "munich": "Muenchen"}


def discover_detail(raw_dir: Path) -> list[tuple[str, date, Path]]:
    """Findet raw/detail/<stadt>/<datum>/listings.csv.gz."""
    found: list[tuple[str, date, Path]] = []
    detail = raw_dir / "detail"
    if not detail.is_dir():
        return found
    for stadt_dir in sorted(detail.iterdir()):
        if not stadt_dir.is_dir() or stadt_dir.name.lower() not in CITY_DIRS:
            continue
        for snap_dir in sorted(stadt_dir.iterdir()):
            datei = snap_dir / "listings.csv.gz"
            if datei.is_file() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", snap_dir.name):
                found.append((CITY_DIRS[stadt_dir.name.lower()],
                              date.fromisoformat(snap_dir.name), datei))
    return found


def columns_of(con: duckdb.DuckDBPyConnection, path: Path) -> set[str]:
    reader = "read_csv_auto(?, header = true, compression = 'gzip')"
    rows = con.execute(f"SELECT * FROM {reader} LIMIT 0", [str(path)]).description
    return {r[0].lower() for r in rows}


def build_union(con: duckdb.DuckDBPyConnection, snapshots) -> str:
    selects = []
    for city, snap, path in snapshots:
        present = columns_of(con, path)
        exprs = []
        for target, expr in COLUMN_EXPRESSIONS.items():
            quelle = re.search(r'"([^"]+)"', expr)
            name = quelle.group(1) if quelle else None
            if name and name.lower() not in present:
                exprs.append(f"CAST(NULL AS {NULL_TYPES[target]}) AS {target}")
            else:
                exprs.append(f"{expr} AS {target}")
        selects.append(
            "SELECT\n"
            f"        '{city}' AS city,\n"
            f"        DATE '{snap.isoformat()}' AS snapshot_date,\n"
            f"        '{path.parent.name}' AS source_file,\n"
            "        " + ",\n        ".join(exprs) + "\n"
            f"      FROM read_csv_auto('{path}', header = true, compression = 'gzip')"
        )
    return "\n    UNION ALL BY NAME\n    ".join(selects)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    raw_dir, db_path = Path(args.raw_dir), Path(args.db)
    snapshots = discover_detail(raw_dir)
    if not snapshots:
        raise SystemExit(
            f"Keine Detail-Snapshots unter {raw_dir}/detail gefunden.\n"
            "Erst laden: python3 download_data.py (im Analyse-Repo) "
            "oder scripts/download_data.sh fuer die vis-Dateien."
        )

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    con.execute(
        "CREATE OR REPLACE TABLE raw.listings_detail AS\n"
        "    SELECT * FROM (\n    " + build_union(con, snapshots) + "\n    ) AS alle\n"
    )
    con.execute("DROP TABLE IF EXISTS raw.load_log_detail")
    con.execute(
        """
        CREATE TABLE raw.load_log_detail AS
        SELECT source_file, city, snapshot_date, COUNT(*) AS row_count,
               COUNT(occupancy_l365d) FILTER (WHERE occupancy_l365d > 0) AS occ_positiv,
               COUNT(DISTINCT last_scraped) AS scrape_tage,
               MIN(last_scraped) AS scraped_von,
               MAX(last_scraped) AS scraped_bis,
               MIN(CURRENT_TIMESTAMP) AS loaded_at
        FROM raw.listings_detail
        GROUP BY ALL
        ORDER BY city, snapshot_date
        """
    )

    print(f"Warehouse: {db_path}")
    print(f"Detail-Snapshots geladen: {len(snapshots)}")
    for row in con.execute(
        "SELECT city, snapshot_date, row_count, occ_positiv, scrape_tage, "
        "scraped_von, scraped_bis FROM raw.load_log_detail "
        "ORDER BY city, snapshot_date"
    ).fetchall():
        anteil = row[3] / row[2] if row[2] else 0
        print("  {:<9} {}  {:>7} Zeilen  {:>7} mit Auslastung ({:.1%})  "
              "Scrape {} Tage: {} bis {}".format(
                  *[str(v) for v in row[:3]], row[3], anteil,
                  row[4], row[5], row[6]))
    con.close()


if __name__ == "__main__":
    main()
