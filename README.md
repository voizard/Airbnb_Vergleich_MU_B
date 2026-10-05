# dbt-Airbnb-Analytics: Berlin & München

Ein dbt-Projekt, das Inside-Airbnb-Rohdaten aus mehreren Snapshots in
auswertbare Marts überführt — von der Roh-CSV bis zur Power-BI-Tabelle.

Entstanden als Portfolio-Projekt, um die Transformationsschicht
(SQL, Warehouse-Denken, Tests, Dokumentation, Versionierung) praktisch
nachzuweisen — ergänzend zu PL-300/Power BI.

## Zielsetzung

Die Frage hinter dem Projekt: **Wie entwickelt sich das Airbnb-Angebot in
Berlin und München über die Zeit — und wie belastbar sind die Daten
überhaupt?**

Beantwortet wird das mit einem klassischen ELT-Aufbau:

```
Inside Airbnb CSVs          EL (Python/DuckDB)         T (dbt)
┌──────────────────┐       ┌──────────────────┐      ┌─────────────────────┐
│ vis/berlin-*.csv │──────▶│  raw.listings_all│─────▶│ staging (Views)     │
│ vis/munich-*.csv │       │  raw.neighbourhoods     │  stg_airbnb__*      │
│ hist/berlin-*.csv│       │  raw.load_log    │      └─────────┬───────────┘
│ hist/munich-*.csv│       └──────────────────┘                │
└──────────────────┘                                           ▼
                                            ┌──────────────────────────────────┐
                                            │ marts (Tables)                   │
                                            │ dim_neighbourhood                │
                                            │ fct_listing_snapshot (inkrem.)   │
                                            │ mart_district_kpis               │
                                            │ mart_price_trend                 │
                                            │ mart_powerbi_listings            │
                                            └──────────────┬───────────────────┘
                                                           ▼
                                                    Power BI / Ad-hoc-SQL
```

## Datenquelle

[Inside Airbnb](https://insideairbnb.com/get-the-data/) —
`visualisations/listings.csv` je Stadt und Snapshot.

| Stadt | Snapshots | Listings gesamt |
|---|---|---|
| Berlin | 2015-09-01 (historisch), 2025-12-27, 2026-03-28, 2026-06-26 | 48.554 |
| München | 2020-05-24 (historisch), 2025-12-29, 2026-03-30, 2026-06-29 | 26.344 |

Rohdaten liegen **nicht** im Repo (Größe, Lizenz). Sie werden per
`scripts/download_data.sh` bzw. manuell bezogen und über
`scripts/load_raw.py` in das DuckDB-Warehouse geladen.

### Historische Snapshots

Zwei ältere Mirrors mit abweichendem Schema sind Teil des Builds:

| Stadt | Stand | Listings | Preis-Abdeckung |
|---|---|---|---|
| Berlin | 2015-09-01 | 15.373 | 100 % |
| München | 2020-05-24 | 11.128 | 100 % |

Der München-Snapshot 2020-05-24 liegt nur in einem älteren Schema vor: Die
Bezirke stehen in `neighbourhood_cleansed` (25 Stadtbezirke), ein
`neighbourhood_group` gibt es nicht. `scripts/load_raw.py` bildet das über einen
Per-Snapshot-Spalten-Override (`subdistrict` → `neighbourhood_cleansed`) auf das
einheitliche Schema ab; Berlin 2015 nutzt `neighbourhood` unverändert.

## Datenmodell

| Modell | Materialisierung | Korn |
|---|---|---|
| `stg_airbnb__listings` | view | eine Zeile je Listing und Snapshot |
| `stg_airbnb__neighbourhoods` | view | eine Zeile je Stadtteil |
| `dim_neighbourhood` | table | eine Zeile je Stadt und Bezirk |
| `fct_listing_snapshot` | **incremental** (delete+insert) | eine Zeile je Stadt, Snapshot und Listing |
| `mart_district_kpis` | table | eine Zeile je Stadt, Bezirk und Snapshot |
| `mart_price_trend` | table | Kennzahlen plus Veränderung zum Vorgänger-Snapshot |
| `mart_powerbi_listings` | table | flache Export-Tabelle (74.898 Zeilen) |
| `snapshots.listings_history` | dbt snapshot (SCD2) | eine Zeile je Listing-Version |

Analyseebene: Berlin hat 12 Bezirke in `neighbourhood_group` (die feinere
`neighbourhood`-Spalte enthält 138 Ortsteile), München hat dort leere Werte und
liefert 25 Stadtbezirke über `neighbourhood`. Das Projekt vereinheitlicht beides
zu `analysis_district` (siehe `stg_airbnb__listings`).

## Ausgewählte Ergebnisse (Stand 2026-06)

**Median-Nachtpreis, teuerste Bezirke**

| Berlin | € | München | € |
|---|---|---|---|
| Pankow | 152 | Altstadt-Lehel | 276 |
| Mitte | 151 | Schwanthalerhöhe | 225 |
| Friedrichshain-Kreuzberg | 139 | Maxvorstadt | 201 |
| Lichtenberg | 122 | Ludwigsvorstadt-Isarvorstadt | 183,50 |
| Charlottenburg-Wilm. | 118 | Au-Haidhausen | 166 |

- Berlin 2026-06: 12.855 Listings, 66,2 % mit auswertbarem Preis
- München 2026-06: 6.890 Listings, 64,8 % mit auswertbarem Preis
- Preisausreißer über 1.000 €/Nacht: Berlin 27, München 156 — werden aus den
  Medians ausgeschlossen, aber gezählt
- Berlin 2015-09: Median der Bezirksmediane 50 € (historischer Vergleichswert)
- München 2020-05: Median der Bezirksmediane 75 €; ganze Wohnungen 95 € →
  2026-06: 178 € (+87 % nominal) — Mai 2020 fiel in den Corona-Lockdown,
  daher als Obergrenze zu lesen

## Tests und Datenqualität

`dbt build` läuft mit **44 bestandenen Tests und 1 Warnung** (36 generic +
3 singular Tests). Die Warnung ist gewollt und dokumentiert:

- `assert_snapshot_drift` (warn) erkennt Zeilenzahl-Sprünge zwischen Snapshots:
  Berlin 2026-03 **−59,5 %**, Berlin 2026-06 **+119,5 %**, München 2025-12
  **−57,2 %** (nach dem 2020er-Snapshot), München 2026-06 **+93,1 %**
- `assert_preis_plausibel` prüft negative Preise und Mediane ohne Datenbasis
- `assert_eindeutiges_listing_je_snapshot` ersetzt einen dbt_utils-Test
  (das Projekt läuft bewusst ohne externe Pakete)

Details: [docs/data_quality.md](docs/data_quality.md)

## Setup und Ausführung

Voraussetzungen: Python 3.13, `dbt-core` + `dbt-duckdb` (siehe `requirements.txt`).

```bash
python3 -m pip install --user -r requirements.txt
export PATH="$HOME/.local/bin:$PATH"
export DBT_PROFILES_DIR=.          # profiles.yml im Repo-Wurzelverzeichnis

python3 scripts/load_raw.py        # EL: CSVs -> data/airbnb.duckdb (Schema raw)
dbt debug                          # Verbindung prüfen
dbt build                          # Seeds, Snapshots, Modelle, Tests
dbt docs generate && dbt docs serve # Dokumentation und Lineage
```

Wichtige Einzelbefehle:

```bash
dbt build --full-refresh                    # alles neu aufbauen
dbt run --select fct_listing_snapshot       # nur das inkrementelle Modell
dbt test --select mart_district_kpis        # Tests eines Marts
dbt source freshness                        # Aktualität der Rohdaten
```

Umgebungsvariablen: `AIRBNB_RAW_DIR` (Standard: `../airbnb/raw`),
`AIRBNB_DUCKDB` (Standard: `data/airbnb.duckdb`).

## Power BI

`mart_powerbi_listings` ist die Konsumenten-Tabelle: flach, deutsch beschriftete
Zimmertypen, Datumsteile für die Zeitachse, Bezirksattribute für Drill-downs.
Verbindung über den DuckDB-ODBC-Treiber; alternativ als CSV exportierbar.

## Continuous Integration

`.github/workflows/dbt_ci.yml` lädt bei jedem Push zwei aktuelle
Inside-Airbnb-Snapshots, baut das Warehouse neu auf und führt `dbt build` aus.
Der Workflow ist lokal mit demselben Ablauf getestet; ein Lauf in GitHub Actions
steht noch aus (kein GitHub-Zugang aus dieser Umgebung).

## Grenzen und nächste Schritte

- Preise fehlen in den Snapshots 2025-12 (beide Städte) und 2026-03 (Berlin);
  belastbare Preisvergleiche gibt es daher für 2015 → 2026-06 (Berlin) und
  2020-05 → 2026-06 (München). Der München-Wert 2020 fällt in den
  Corona-Lockdown und ist als Obergrenze zu lesen.
- Nur `visualisations`-Daten; `calendar`/`reviews` (Auslastung, Umsatzschätzung)
  fehlen.
- Ausbaufähig: `dbt_utils`-Pakete, CI-Badge, Geo-Export (GeoJSON) für Karten.

## Lizenz

Code: MIT (siehe `LICENSE`). Daten: Inside Airbnb, eigene Lizenzbedingungen
beachten (Attribution, keine kommerzielle Weitergabe der Rohdaten).
