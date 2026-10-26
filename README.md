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
                                            │ dim_district_snapshot            │
                                            │ dim_district_verfuegbarkeit      │
                                            │ fct_listing_snapshot (inkrem.)   │
                                            │ mart_district_kpis               │
                                            │ mart_price_trend                 │
                                            │ mart_powerbi_listings            │
                                            │ mart_powerbi_report_schlank      │
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
| `dim_district_snapshot` | table | Kennzahlen je Bezirk und Snapshot (148 Zeilen), nicht additiv |
| `dim_district_verfuegbarkeit` | table | Verfügbarkeit und Preis je Bezirk und Snapshot (148 Zeilen), nicht additiv |
| `fct_listing_snapshot` | **incremental** (delete+insert) | eine Zeile je Stadt, Snapshot und Listing |
| `mart_district_kpis` | table | eine Zeile je Stadt, Bezirk und Snapshot |
| `mart_price_trend` | table | Kennzahlen plus Veränderung zum Vorgänger-Snapshot |
| `mart_powerbi_listings` | table | flache Export-Tabelle (74.898 Zeilen) |
| `mart_powerbi_report_schlank` | table | schlanke Faktentabelle für Power BI (74.898 Zeilen, 33 Spalten) |
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
- Berlin 2015-09 → 2026-06, ganze Unterkünfte: 65 € → 155 € (+138 % nominal)
- München 2020-05: Median der Bezirksmediane 75 €; ganze Wohnungen 95 € →
  2026-06: 178 € (+87 % nominal) — Mai 2020 fiel in den Corona-Lockdown,
  daher als Obergrenze zu lesen

## Tests und Datenqualität

`dbt build` läuft mit **44 bestandenen Tests und 1 Warnung** (42 generic +
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
python3 scripts/export_powerbi_de.py # Power-BI-CSVs in deutscher Schreibweise
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

Drei Tabellen bilden die Konsumentenschicht:

- `mart_powerbi_report_schlank` — Faktentabelle, eine Zeile je Inserat und
  Snapshot (74.898 Zeilen, 33 Spalten): Preise, Zimmertyp, Koordinaten,
  Bezirksattribute, `snapshot_label` („Juni 2026") und `district_snapshot_id`
  als Fremdschlüssel.
- `dim_district_snapshot` — Bezirkskennzahlen je Snapshot (148 Zeilen):
  Median- und Durchschnittspreis, Preis-Abdeckung, Ausreißerzahl sowie die
  Veränderung zum vorherigen Snapshot mit Preisen. Nicht additiv (Median,
  Anteile) und unabhängig von Filtern der Faktentabelle — nur lesen, nie summieren.
- `dim_district_verfuegbarkeit` — Verfügbarkeit je Bezirk und Snapshot
  (148 Zeilen, gleicher Primärschlüssel wie `dim_district_snapshot`): Anteile
  der Inserate mit 0, 1–89, 90–299 und ab 300 freien Tagen, Mittel und Median
  der freien Tage sowie Median- und Mittelpreis. Eigene Tabelle, weil Power BI
  die Spaltenzahl beim Import festschreibt — zusätzliche Spalten in einer
  bestehenden Datei fallen dort still heraus.

`mart_powerbi_listings` bleibt als flache Variante ohne Bezirks-Fremdschlüssel
erhalten. Verbindung über den DuckDB-ODBC-Treiber; alternativ als CSV.

### CSV-Export in deutscher Schreibweise

DuckDB schreibt Dezimalzahlen mit Punkt (`26.0`). Power BI liest mit deutscher
Locale und deutet den Punkt als Tausendertrennzeichen — aus `26.0` wird `260`
(Faktor 10). `scripts/export_powerbi_de.py` schreibt daher alle reinen
Zahlenfelder mit Dezimalkomma, Semikolon als Trennzeichen, UTF-8 mit BOM:

```bash
python3 scripts/export_powerbi_de.py        # dim_district_snapshot + dim_district_verfuegbarkeit + mart_powerbi_report_schlank
python3 scripts/export_powerbi_de.py --alle # alle Marts
```

Textfelder (`Charlottenburg-Wilm.`) und Ganzzahlen bleiben unangetastet. Beim
Import in Power BI: Zahlen mit Gebietsschema **Deutsch**, die Wahr/Falsch-Spalten
(`has_price`, `is_price_outlier`, …) mit **Englisch (USA)** — im CSV stehen
`true`/`false`.

**Seite 1 „Preisentwicklung"** — nur ganze Unterkünfte, Median je Inserat,
Ausreißer über 1.000 €/Nacht ausgeschlossen, Stand Juni 2026: 6,11 Tsd. Inserate
in Berlin bei 69 % Preis-Abdeckung, 2,77 Tsd. in München bei 60 %. Die beiden
Kacheln rechts zeigen den Median-Nachtpreis mit Startwert und Veränderung
(178 € ab 95 €, +87,37 % für München; 155 € ab 65 €, +138,46 % für Berlin).
Das Säulendiagramm stellt denselben Median je Snapshot gegenüber: Berlin
2015-Q3 65 € und 2026-Q2 155 €, München 2020-Q2 95 €, 2026-Q1 182 € und
2026-Q2 178 €. Die Achse ist kategorial und chronologisch sortiert, damit die
beiden Städte mit ihren unterschiedlichen Snapshot-Daten nebeneinander lesbar
bleiben.

![Startseite des Power-BI-Berichts: Preisentwicklung Berlin und München](docs/powerbi_startseite.png?v=3)

**Seite 2 „Verfügbarkeit"** — nur ganze Unterkünfte, Median je Inserat, Stand
26./29. Juni 2026: Median-Nachtpreis 155 € in Berlin gegen 178 € in München,
dazu eine Median-Verfügbarkeit von 168 gegen 61 freien Tagen im Jahr. Das
Streudiagramm stellt je Bezirk Median-Preis gegen Median-Verfügbarkeit,
Blasengröße = Zahl der Inserate: Berlin liegt geschlossen im Feld hoher
Verfügbarkeit (rund 150–260 freie Tage) bei Preisen um 100–160 €, München
streut breit nach unten (viele Bezirke unter 130 freie Tage) und hat zugleich
die teureren Bezirke. Verfügbarkeit ist host-gesteuert — hohe Werte heißen
„viel angeboten", nicht „wenig gebucht".

![Seite 2 des Power-BI-Berichts: Verfügbarkeit Berlin und München](docs/powerbi_verfuegbarkeit.png?v=2)

**Seite 3 „Bezirke"** — Bezirksvergleich, Median je Bezirk, Stand Juni 2026:
Der günstigste Bezirk ist Berlin **Neukölln mit 47 €**, der teuerste **Spandau
mit 78 €**; in München liegt **Milbertshofen-Am Hart mit 83 €** vorn und
**Altstadt-Lehel mit 160 €** am oberen Ende. Das Ranking steckt im Measure, weil
eine Kachel nicht selbst sortieren kann (`TOPN` + `CONCATENATEX`, aufsteigend für
den günstigsten, absteigend für den teuersten Bezirk); die Mindestbasis von 30
Inseraten mit Preis verhindert, dass ein Bezirk mit einer Handvoll Angebote die
Kachel gewinnt.

**Vorbehalt dieser Seite:** Sie ist die einzige ohne `snapshot_label`-Filter — es
werden also alle Snapshots mit Preisen gemeinsam ausgewertet. Das verzerrt das
Ergebnis, denn die alten Stände sind billiger **und** zahlenmäßig viel größer:
Neukölln kommt aus 2015 mit 2.336 Zeilen (Median 42 €) und aus 2026-06 mit nur
677 Zeilen (Median 117 €) — der alte Stand stellt 77,5 % aller Zeilen. Der
günstigste Bezirk ist damit nicht der billigste, sondern der mit dem größten
Altbestand. Die Gegenprobe: Auf Juni 2026 eingeschränkt ist Berlin-Neukölln mit
117 € **nicht** mehr günstigster Bezirk, sondern liegt im Mittelfeld; günstigster
ist Reinickendorf (83 €, ganze Unterkünfte 101 €). Dasselbe Muster in München:
Milbertshofen-Am Hart bezieht 64,7 % seiner Zeilen aus dem Corona-Snapshot 2020
(Median 69 €) und steht deshalb oben, im Juni 2026 liegt es bei 116 €.

Ein Bezirks-Ranking ohne `snapshot_label`-Slicer misst also den Snapshot-Mix,
nicht das Preisniveau. Für eine belastbare Aussage gehören `city`- **und**
`snapshot_label`-Slicer neben die Kachel; dann lautet sie Reinickendorf 101 €
gegen Mitte 170 € (Berlin) bzw. Aubing-Lochhausen-Langwied 110 € gegen
Altstadt-Lehel 336,50 € (München), jeweils ganze Unterkünfte. Ein Vorbehalt der
Seite selbst: Die Auswahl steht auf *keinem* Zimmertyp, also werden alle vier
Typen gemischt.

![Seite 3 des Power-BI-Berichts: Bezirksvergleich Berlin und München](docs/powerbi_bezirke.png)

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
