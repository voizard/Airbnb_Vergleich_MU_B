# Measures: Median-Nachtpreis (Bezirk · Stadt · Trend)

Stand 2026-10-20 · Projekt: Inside-Airbnb-Marktanalyse (Berlin + München)

**Tabellennamen:** `fct` = deine Faktentabelle (`mart_powerbi_report_schlank`),
`dim_neighbourhood` = Bezirksdimension, `dim_snapshot` = Snapshot-Dimension.
Wenn deine Tabellen anders heißen, nur die Namen tauschen – die Logik bleibt.

---

## 0. Grundregel: nie SUM auf Preise

Ein Preis ist keine Menge. `SUM(price_eur)` über einen Bezirk ergibt keine Kennzahl,
sondern die Summe aller Angebotspreise – in Berlin 2026-06 wären das ~1,3 Mio. €.

In Power BI deshalb:

1. Spalte `price_eur` in der Feldliste markieren → *Zusammenfassung* → **Nicht zusammenfassen**
   (oder **Median**). Nie *Summe*.
2. Für Kacheln und Karten die Measures unten nehmen – die rechnen im jeweiligen
   Filterkontext, auch wenn du nach Zimmertyp oder Zeitraum einschränkst.

---

## 1. Median-Nachtpreis (im aktuellen Filterkontext)

```dax
Median-Nachtpreis =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    fct[has_price] = TRUE,
    fct[is_price_outlier] = FALSE
)
```

Nenner sind nur Inserate **mit** Preis. Ohne Preis kein Wert – nicht 0.

## 2. Nur ganze Wohnungen (empfohlene Vergleichsbasis)

```dax
Median-Nachtpreis ganzes Objekt =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    fct[has_price] = TRUE,
    fct[is_entire_home] = TRUE,
    fct[is_price_outlier] = FALSE
)
```

Gemischt über alle Zimmertypen ist der Wert nicht vergleichbar – Privatzimmer liegen
deutlich unter ganzen Wohnungen.

## 3. Datenbasis sichtbar machen (in jeden Tooltip)

```dax
Inserate mit Preis =
CALCULATE ( COUNTROWS ( fct ), fct[has_price] = TRUE )

Preis-Abdeckung % =
DIVIDE (
    CALCULATE ( COUNTROWS ( fct ), fct[has_price] = TRUE ),
    COUNTROWS ( fct )
)

Median-Preis Ausreißer > 1000 € =
CALCULATE ( COUNTROWS ( fct ), fct[is_price_outlier] = TRUE )
```

Ein Bezirks-Median aus 92 Inseraten ist etwas anderes als einer aus 2.032.

## 4. Stadt-Median (Median über Listings, NICHT über Bezirke)

```dax
Median-Nachtpreis Stadt =
CALCULATE ( [Median-Nachtpreis], REMOVEFILTERS ( dim_neighbourhood ) )
```

**Wichtig:** Ein Median von Bezirks-Medianen ist **nicht** der Stadt-Median – er
gewichtet jeden Bezirk gleich, egal wie viele Inserate dort stehen. Beleg aus dem
Bestand (Berlin 2026-06-26, Inserate mit Preis, ohne > 1.000 €):

| Wert | Ergebnis |
| --- | --- |
| Mittel über alle Listings | 154,26 € |
| **Median über alle Listings** | **130,00 €** |
| Mittel der Bezirks-Mediane | 118,13 € ← falscher Weg |
| Median der Bezirks-Mediane | 116,50 € ← auch falscher Weg |

## 5. Trend zum Vor-Snapshot (ungleichmäßige Snapshots)

```dax
Median-Nachtpreis Vor-Snapshot =
VAR Aktuell = MAX ( fct[snapshot_date] )
VAR Vorher  =
    CALCULATE (
        MAX ( fct[snapshot_date] ),
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] < Aktuell
    )
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] = Vorher
    )

Veränderung zum Vor-Snapshot % =
DIVIDE ( [Median-Nachtpreis] - [Median-Nachtpreis Vor-Snapshot],
         [Median-Nachtpreis Vor-Snapshot] )
```

`DATEADD` / `SAMEPERIODLASTYEAR` bewusst nicht verwenden: die Snapshots liegen
2015-09, 2020-05, 2025-12, 2026-03, 2026-06 – also unregelmäßig, ohne Jahrgangspaar.
Das Measure nimmt immer den **zeitlich nächstgelegenen früheren Snapshot**.

Für die Bezirkstabelle gibt es dieselbe Zahl schon fertig als Spalte
`district_prev_median_price_eur` / `district_price_change_share` in
`dim_district_snapshot` – dort nur auf Bezirk × Snapshot lesen, **niemals summieren**.

## 6. Warum Median und nicht Mittel – Zahlen aus dem Bestand

Berlin 2026-06-26, Bezirke, Inserate mit Preis, Ausreißer > 1.000 € ausgeschlossen:

| Bezirk | Inserate | Mittel | Median | Abweichung |
| --- | ---: | ---: | ---: | ---: |
| Mitte | 2.032 | 174,51 € | 151,00 € | +23,51 € |
| Pankow | 1.244 | 171,16 € | 152,00 € | +19,16 € |
| Spandau | 119 | 155,53 € | 116,00 € | +39,53 € |
| Friedrichshain-Kreuzberg | 1.658 | 154,74 € | 139,00 € | +15,74 € |
| Charlottenburg-Wilmersdorf | 1.046 | 146,60 € | 118,00 € | +28,60 € |
| Tempelhof-Schöneberg | 587 | 143,82 € | 116,00 € | +27,82 € |
| Lichtenberg | 259 | 137,52 € | 122,00 € | +15,52 € |
| Neukölln | 677 | 132,33 € | 117,00 € | +15,33 € |
| Treptow-Köpenick | 400 | 129,03 € | 107,00 € | +22,03 € |
| Marzahn-Hellersdorf | 92 | 120,12 € | 97,50 € | +22,62 € |
| Steglitz-Zehlendorf | 251 | 118,11 € | 99,00 € | +19,11 € |
| Reinickendorf | 124 | 93,78 € | 83,00 € | +10,78 € |

Das Mittel liegt in **jedem** Bezirk über dem Median (10–40 €), weil die teuren
Inserate nach oben ziehen. Auf Stadtebene ist der Effekt größer:
München 2026-06-29 – Mittel 195,88 €, Median 143,00 € (**53 € Unterschied**).

Auch die 1.000-€-Grenze wirkt asymmetrisch (Berlin 2026-06-26, 8.515 Inserate mit
Preis, davon 26 über 1.000 €):

| | mit allen Preisen | ohne > 1.000 € |
| --- | ---: | ---: |
| Mittel | 160,59 € | 154,26 € |
| Median | 131,00 € | 130,00 € |

Der Median bewegt sich um 1 €, das Mittel um 6 €. Deshalb: **Median zeigen, Mittel
höchstens als Vergleichslinie.**

## 7. Ganze Wohnungen – die saubere Vergleichsbasis (Median)

| Stadt | Snapshot | Inserate | Mittel | Median |
| --- | --- | ---: | ---: | ---: |
| Berlin | 2015-09-01 | 9.336 | 74,01 € | 65,00 € |
| Berlin | 2026-06-26 | 6.113 | 172,88 € | 155,00 € |
| München | 2020-05-24 | 6.277 | 129,08 € | 95,00 € |
| München | 2026-03-30 | 2.239 | 230,58 € | 182,00 € |
| München | 2026-06-29 | 2.772 | 233,05 € | 178,00 € |

## 8. Kacheln: teuerster und günstigster Bezirk

Kacheln (Card) können nicht sortieren — das Ranking gehört ins Measure, das Measure
gibt Text zurück. `Fakt` = Faktentabelle (`mart_powerbi_report_schlank`).

```dax
Teuerster Bezirk =
VAR Bezirke =
    ADDCOLUMNS (
        VALUES ( Fakt[district] ),
        "@Preis", [Median-Nachtpreis],
        "@N", CALCULATE ( COUNTROWS ( Fakt ), Fakt[has_price] = TRUE )
    )
VAR Kandidaten =
    FILTER ( Bezirke, NOT ISBLANK ( [@Preis] ) && [@N] >= 30 )
VAR Sieger = TOPN ( 1, Kandidaten, [@Preis], DESC )
RETURN CONCATENATEX ( Sieger, Fakt[district], " / " )

Guenstigster Bezirk =
VAR Bezirke =
    ADDCOLUMNS (
        VALUES ( Fakt[district] ),
        "@Preis", [Median-Nachtpreis],
        "@N", CALCULATE ( COUNTROWS ( Fakt ), Fakt[has_price] = TRUE )
    )
VAR Kandidaten =
    FILTER ( Bezirke, NOT ISBLANK ( [@Preis] ) && [@N] >= 30 )
VAR Sieger = TOPN ( 1, Kandidaten, [@Preis], ASC )
RETURN CONCATENATEX ( Sieger, Fakt[district], " / " )
```

Mit Preis in der Kachel: `... & " – " & FORMAT ( [@Preis], "#,##0" ) & " €"`.

`"#,##0"` = ganze Zahl mit Tausenderpunkt (de-DE rendert das Komma als Punkt).
`"#.0"` wäre eine Dezimalstelle — also `152,0 €` statt `152 €`.
Fuer eine echte Zahlkachel nicht `FORMAT` nehmen, sondern den Wert direkt ins Feld
und im Visual unter Format -> Wert -> Dezimalstellen = 0 setzen: bleibt Zahl,
nur die Anzeige ist ganzzahlig.

**Die ISBLANK-Prüfung ist beim günstigsten Bezirk Pflicht:** In DAX sortiert BLANK
vor jeder Zahl. Ohne den Filter gewinnt in aufsteigender Reihenfolge ein Bezirk
ohne Preise (Berlin 12/2025 + 03/2026, München 12/2025) — die Kachel zeigt dann
einen leeren Bezirksnamen.

### Werte aus dem Bestand (Juni 2026, alle Zimmertypen, ohne Ausreißer)

| Stadt | günstigster | € | teuerster | € |
| --- | --- | ---: | --- | ---: |
| Berlin | Reinickendorf | 83,0 | Pankow | 152,0 |
| München | Aubing-Lochhausen-Langwied | 110,0 | Altstadt-Lehel | 276,0 |

Nur ganze Objekte (n >= 30): Berlin günstigster **Reinickendorf 101 €**,
teuerster **Mitte 170 €**; München günstigster **Aubing-Lochhausen-Langwied 110 €**.

## 9. Merksätze

- Preis = Angebotspreis pro Nacht je **Inserat**, nicht je Buchung, nicht je Gast.
- Immer **Median**, nie Summe, nie Mittel als Hauptzahl.
- Immer die **Abdeckung** mitzeigen (`Preis-Abdeckung %`): Berlin 2025-12 und 2026-03
  sowie München 2025-12 liefern gar keine Preise → dort ist der Wert leer, nicht 0.
- Stadtwerte über **Listings** rechnen, nicht über Bezirkswerte mitteln.
- Snapshot-Vergleich ist kein Same-Store-Vergleich: Zu- und Abgänge verändern die
  Grundgesamtheit, nicht nur die Preise.
- Bezirks-Rankings (teuerster/günstigster) ohne `city`-Slicer zeigen immer München.
- Günstigste Bezirke kippen stärker mit Zimmertyp und Mindest-n als teure: Berlin
  ist über alle Typen Reinickendorf (83 €), über ganze Objekte Mitte als Gegenspieler
  — der günstigste bleibt Reinickendorf, aber +18 €.
