#!/usr/bin/env python3
"""Exportiert die Power-BI-Marts als CSV in deutscher Schreibweise.

Warum dieses Skript
-------------------
DuckDB schreibt Dezimalzahlen immer mit Punkt (`26.0`). Power BI liest die Dateien
mit deutscher Locale und deutet den Punkt als Tausendertrennzeichen: aus `26.0`
wird still `260` (Faktor 10). Deshalb schreibt dieses Skript alle reinen
Zahlenfelder mit Dezimalkomma - Semikolon als Trennzeichen, UTF-8 mit BOM,
ISO-Datum, kein Tausendertrennzeichen. Dann stimmt der Import mit deutscher
Locale ohne Zusatzschritt.

Textfelder wie `Charlottenburg-Wilm.` oder `Berlin|Mitte` bleiben unangetastet,
weil nur Felder der Form `-?Zahl.Zahl` umgeschrieben werden. Ganzzahlen (IDs,
Zaehler, Jahre) bleiben unveraendert.

Aufruf (aus dem Ordner `dbt-airbnb/`)
-------------------------------------
    python3 scripts/export_powerbi_de.py                # Standardtabellen
    python3 scripts/export_powerbi_de.py --alle         # alle Marts
    python3 scripts/export_powerbi_de.py --ziel ../powerbi-export

Voraussetzung: `dbt run` hat die Marts gebaut (DuckDB: data/airbnb.duckdb).
"""

from __future__ import annotations

import csv
import os
import re
import sys

import duckdb

PROJEKT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(PROJEKT, "data", "airbnb.duckdb")

# Tabelle -> Spalte fuer die stabile Zeilenreihenfolge im Export
STANDARD = {
    "dim_district_snapshot": "district_snapshot_id",
    "dim_district_verfuegbarkeit": "district_snapshot_id",
    "mart_powerbi_report_schlank": "listing_snapshot_id",
}
ALLE = {
    "dim_neighbourhood": "district_key",
    "dim_district_snapshot": "district_snapshot_id",
    "mart_district_kpis": "district_key",
    "mart_powerbi_listings": "listing_snapshot_key",
    "mart_powerbi_report_schlank": "listing_snapshot_id",
    "mart_price_trend": "city",
}
MUSTER = re.compile(r"^-?\d+\.\d+$")


def ziel_aus_argumenten() -> str:
    if "--ziel" in sys.argv:
        return os.path.abspath(sys.argv[sys.argv.index("--ziel") + 1])
    return os.path.abspath(os.path.join(PROJEKT, "..", "powerbi-export"))


def deutsches_komma(pfad: str) -> int:
    """Schreibt reine Zahlenfelder mit Komma um und setzt UTF-8-BOM. Gibt die Anzahl zurueck."""
    with open(pfad, "r", encoding="utf-8-sig", newline="") as f:
        zeilen = list(csv.reader(f, delimiter=";"))
    geaendert = 0
    for zeile in zeilen[1:]:
        for i, wert in enumerate(zeile):
            if MUSTER.match(wert):
                zeile[i] = wert.replace(".", ",")
                geaendert += 1
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, delimiter=";", lineterminator="\n").writerows(zeilen)
    return geaendert


def main() -> int:
    tabellen = dict(ALLE) if "--alle" in sys.argv else dict(STANDARD)
    ziel = ziel_aus_argumenten()
    os.makedirs(ziel, exist_ok=True)
    con = duckdb.connect(DB, read_only=True)
    vorhanden = {r[0] for r in con.execute(
        "select table_name from duckdb_tables() where schema_name = 'airbnb_marts'").fetchall()}
    print(f"Ziel: {ziel}\n")
    for tabelle, sortierspalte in tabellen.items():
        if tabelle not in vorhanden:
            print(f"  {tabelle:<32} uebersprungen (nicht im Warehouse)")
            continue
        pfad = os.path.join(ziel, f"{tabelle}.csv")
        con.execute(
            f"copy (select * from airbnb_marts.{tabelle} order by {sortierspalte}) "
            f"to '{pfad}' (format csv, delimiter ';', header true)"
        )
        n = deutsches_komma(pfad)
        groesse = os.path.getsize(pfad) / 1024 / 1024
        print(f"  {tabelle:<32} {n:>9} Zahlenfelder mit Komma   {groesse:6.1f} MB")
    con.close()
    print("\nFertig. In Power BI die Dateien ersetzen und aktualisieren; "
          "Typ-Schritt auf Dezimalzahl + Deutsch (Deutschland).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
