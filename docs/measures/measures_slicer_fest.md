# Measures: refresh-fest und slicer-gesteuert

Stand 2026-11-04 · Projekt: dbt-airbnb

**Ziel:** Die Measures enthalten **keine festen Daten** mehr. Kommt ein neuer
Snapshot dazu, laufen sie ohne Änderung weiter. Jeder Slicer greift.

---

## 1. Grundregel: keine festen Daten, kein REMOVEFILTERS

Ein Measure, das den Slicer respektieren soll, hat **keine** Datumsangabe und
**kein** `REMOVEFILTERS` auf `snapshot_date`:

```dax
Median-Nachtpreis =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    fct[has_price] = TRUE (),
    fct[is_entire_home] = TRUE (),
    fct[is_price_outlier] = FALSE ()
)
```

Der Slicer setzt den Kontext — nichts anderes. Genau das fehlt aktuell: Deine
Preis-Kacheln enthalten `REMOVEFILTERS` oder `ALL` auf `snapshot_date` und
ignorieren damit den Slicer. Deshalb zeigen sie 94 € / 149 € (über alle
Snapshots gepoolt), während die Verfügbarkeits-Kacheln reagieren.

## 2. Die richtige Datenbasis: eigener Snapshot-Slicer

Die neue Tabelle **`dim_snapshot`** (10 Zeilen, eine je Stand) löst das
Doppel-Format-Problem:

| snapshot_key | snapshot_date | snapshot_label | snapshot_sort |
| ---: | --- | --- | --- |
| 1 | 2015-09-01 | September 2015 | 2015-09 |
| 2 | 2020-05-24 | Mai 2020 | 2020-05 |
| 3 | 2025-12-27 | Dezember 2025 | 2025-12 |
| 4 | 2025-12-29 | Dezember 2025 | 2025-12 |
| 5 | 2026-03-28 | März 2026 | 2026-03 |
| 6 | 2026-03-30 | März 2026 | 2026-03 |
| 7 | 2026-06-26 | Juni 2026 | 2026-06 |
| 8 | 2026-06-29 | Juni 2026 | 2026-06 |
| 9 | 2026-09-19 | September 2026 | 2026-09 |
| 10 | 2026-09-23 | September 2026 | 2026-09 |

**Einbau in Power BI:**

1. `dim_snapshot.csv` laden (deutscher Export wie die anderen Dateien).
2. `snapshot_date` → Typ **Datum**, Gebietsschema **Deutsch (Deutschland)**.
3. Beziehung anlegen: `dim_snapshot[snapshot_date]` **(1)** →
   `mart_powerbi_report_schlank[snapshot_date]` **(n)**, Kreuzfilter **einfach**.
4. **Slicer auf `dim_snapshot[snapshot_label]`** legen, nicht auf die
   Faktentabelle. Sortiere nach `snapshot_sort`, damit „Juni 2026" an der
   richtigen Stelle steht (Textsortierung würde „Dezember" vor „Juni" stellen).
5. Alte Slicer auf `fct[snapshot_date]` entfernen.

Weil `dim_snapshot[snapshot_date]` eindeutig ist, filtert die Beziehung sauber
über alle Tabellen — auch `dim_district_snapshot` und
`dim_district_verfuegbarkeit`, sobald diese über `district_snapshot_id`
verbunden sind.

## 3. Erst- und Letztwert — dynamisch, ohne feste Daten

Für Vergleichskacheln („Entwicklung seit …") die Endpunkte **berechnen** statt
eintragen. So stimmen sie nach jedem Refresh automatisch:

```dax
Erster Snapshot =
CALCULATE ( MIN ( fct[snapshot_date] ), REMOVEFILTERS ( dim_snapshot ) )

Letzter Snapshot =
CALCULATE ( MAX ( fct[snapshot_date] ), REMOVEFILTERS ( dim_snapshot ) )

Median-Nachtpreis erster Snapshot =
VAR Erster = [Erster Snapshot]
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( dim_snapshot ),
        fct[snapshot_date] = Erster
    )

Median-Nachtpreis letzter Snapshot =
VAR Letzter = [Letzter Snapshot]
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( dim_snapshot ),
        fct[snapshot_date] = Letzter
    )

Veränderung % =
DIVIDE (
    [Median-Nachtpreis letzter Snapshot] - [Median-Nachtpreis erster Snapshot],
    [Median-Nachtpreis erster Snapshot]
)
```

`REMOVEFILTERS ( dim_snapshot )` bezieht sich auf die **Dimensions**tabelle,
nicht auf die Faktentabelle — dadurch bleibt die Beziehung intakt und der
Vergleich ist reproduzierbar. Diese Measures brauchen keine Wartung: Ein
neuer Snapshot wird automatisch zum „letzten".

## 4. Verfügbarkeit — gleiche Logik

```dax
Median-Verfügbarkeit =
CALCULATE (
    MEDIAN ( fct[availability_365] ),
    fct[is_entire_home] = TRUE ()
)

Mittlere Verfügbarkeit aktive Inserate =
CALCULATE (
    AVERAGE ( fct[availability_365] ),
    fct[is_entire_home] = TRUE (),
    fct[availability_365] > 0
)

Preis-Abdeckung % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fct ), fct[has_price] = TRUE () ),
    COUNTROWS ( fct )
)
```

**Wichtig zum Mittelwert:** Der Median ist hier die richtige Hauptzahl. Die
Verteilung ist dreigipflig (viele 0-Tage- und viele 300+-Inserate); das Mittel
liegt deutlich daneben (München Juni: Mittel 117,6 gegen Median 61).

## 5. Prüfliste

- [ ] Alle Measures nach `REMOVEFILTERS` / `ALL` mit `snapshot_date` durchsuchen
      → entfernen (außer in den Erst/Letzt-Measures aus Abschnitt 3).
- [ ] Keine `DATE ( 2026, … )`-Literale mehr in Measures.
- [ ] Slicer nur noch auf `dim_snapshot`, nicht auf `fct[snapshot_date]`.
- [ ] `dim_snapshot[snapshot_label]` nach `snapshot_sort` sortieren.
- [ ] Spalten `snapshot_year/quarter/month` in der Faktentabelle können bleiben
      (schaden nicht), der Slicer nutzt aber `dim_snapshot`.
