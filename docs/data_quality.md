# Datenqualität: Befunde aus den Inside-Airbnb-Snapshots

Alle Befunde sind mit Abfragen gegen das Warehouse reproduzierbar und, soweit
sinnvoll, durch Tests abgesichert.

## 1. Preisabdeckung schwankt extrem

| Snapshot | Zeilen | Preis vorhanden |
|---|---|---|
| Berlin 2015-09-01 | 15.373 | 100 % |
| Berlin 2025-12-27 | 14.470 | 0 % |
| Berlin 2026-03-28 | 5.856 | 0 % |
| Berlin 2026-06-26 | 12.855 | 66,2 % |
| München 2025-12-29 | 4.757 | 0 % |
| München 2026-03-30 | 3.569 | 3,0 % |
| München 2026-06-29 | 6.890 | 64,8 % |

**Konsequenz:** Preiskennzahlen sind je Snapshot nur so gut wie die Abdeckung.
`mart_district_kpis` weist `price_coverage_share` aus, damit Mediane nicht
unkommentiert nebeneinander stehen. `mart_price_trend` filtert Snapshots ohne
Median, dadurch entstehen Lücken statt falscher Nullen.
Test: `assert_preis_plausibel` (Median NULL bei vorhandenen Preisen = Fehler).

## 2. Zeilenzahl-Sprünge zwischen Snapshots

| Stadt | Snapshot | Zeilen | Vorgänger | Abweichung |
|---|---|---|---|---|
| Berlin | 2026-03-28 | 5.856 | 14.470 | −59,5 % |
| Berlin | 2026-06-26 | 12.855 | 5.856 | +119,5 % |
| München | 2026-06-29 | 6.890 | 3.569 | +93,1 % |

**Interpretation:** Scraping-Lücken bzw. ein abweichender Erhebungsumfang in der
Quelle, kein echter Marktrückgang. Wer die Zeitreihe ungeprüft liest, deutet
einen Datenfehler als Marktbewegung.
Test: `assert_snapshot_drift` (severity `warn`, Schwelle über
`var('snapshot_drift_schwelle')` = 30 %).

## 3. Schema-Drift im historischen Snapshot

`hist/berlin-github-listings.csv` (2015-09) hat drei Spalten weniger als die
aktuellen Snapshots: `host_profile_id`, `number_of_reviews_ltm`, `license`.

**Konsequenz im Loader:** `scripts/load_raw.py` prüft je Datei die vorhandenen
Spalten und setzt fehlende als typisierten NULL ein (`NULL_TYPES`). Ohne
expliziten Typ hätte `CAST(NULL AS VARCHAR)` im `UNION ALL BY NAME` die Spalte
`reviews_ltm` auf VARCHAR gezogen — genau dieser Fehler ist beim ersten Build
aufgetreten und wurde behoben.

## 4. Preisausreißer

Höchster Wert im gesamten Datensatz: 78.531 €/Nacht. Werte über
`var('max_plausibler_preis_eur')` = 1.000 € gelten als Ausreißer:
Berlin 27 Zeilen, München 136 Zeilen.

**Konsequenz:** Ausreißer werden nicht gelöscht, sondern über
`is_price_outlier` markiert und aus Median/Mittelwert ausgeschlossen;
`price_outlier_count` hält die Zahl sichtbar.

## 5. Unterschiedliche Verwaltungsebenen

- Berlin: `neighbourhood_group` = 12 Bezirke, `neighbourhood` = 138 Ortsteile
- München: `neighbourhood_group` ist durchgehend leer, `neighbourhood` = 25 Stadtbezirke

**Konsequenz:** `analysis_district` = `coalesce(neighbourhood_group, neighbourhood)`
plus `analysis_level` als Herkunftskennzeichen. Die Tests auf `district` sind
deshalb bewusst nicht als `not_null` definiert — München wäre sonst dauerhaft rot.

## 6. Leere Zeile in der Bezirksliste

`berlin/neighbourhoods.csv` enthält eine Zeile ohne Inhalt (139 Zeilen,
138 gültige). Der Loader filtert leere `neighbourhood`-Werte.

## 7. Keine Duplikate auf Listungsebene

Je Stadt und Snapshot ist `listing_id` eindeutig (geprüft über alle sieben
Snapshots). Test: `assert_eindeutiges_listing_je_snapshot`.

## 8. Was der SCD2-Snapshot zeigt

`snapshots.listings_history` enthält 107.593 Zeilen für 38.291 Listings, also
durchschnittlich 2,8 Versionen je Listing. Listings mit Preisänderung lassen
sich über `dbt_valid_from` / `dbt_valid_to` nachvollziehen — Grundlage für
Fragen wie "Wie oft ändern Hosts ihre Preise?".
