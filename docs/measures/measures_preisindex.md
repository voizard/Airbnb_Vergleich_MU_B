# Preis-Index über die Zeit (historischer Vergleich)

Stand 2026-11-04 · Projekt: dbt-airbnb
Tabellen: `fct` = `mart_powerbi_report_schlank`, `dim_snapshot` = Snapshot-Dimension.

**Ziel:** Der historische Vergleich soll sichtbar bleiben — trotz unterschiedlicher
Startjahre (Berlin 2015, München 2020). Lösung: **Index mit Start = 100**.

---

## 1. Die Messpunkte (ganze Unterkünfte, Median, ohne Ausreißer)

| Stadt | Snapshot | Median | Index (Start = 100) |
| --- | --- | ---: | ---: |
| Berlin | 2015-09-01 | 65 € | **100,0** |
| Berlin | 2025-12-27 | — | Lücke (keine Preise) |
| Berlin | 2026-03-28 | — | Lücke (keine Preise) |
| Berlin | 2026-06-26 | 155 € | **238,5** |
| Berlin | 2026-09-19 | 155 € | **238,5** |
| München | 2020-05-24 | 95 € | **100,0** |
| München | 2025-12-29 | — | Lücke (keine Preise) |
| München | 2026-03-30 | 182 € | **191,6** |
| München | 2026-06-29 | 178 € | **187,4** |
| München | 2026-09-23 | 250 € | **263,2** |

Es gibt nur **7 Messpunkte mit Preis** über 11 Jahre. Deshalb ist eine Linie mit
Punkten die ehrlichste Darstellung — nicht ein Balkendiagramm.

---

## 2. Basis-Measure

```dax
Median Nachtpreis =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    fct[is_entire_home] = TRUE (),
    fct[has_price] = TRUE (),
    fct[is_price_outlier] = FALSE ()
)
```

---

## 3. Startpreis — dynamisch, kein festes Datum

Sucht selbst den **ersten Snapshot mit Preis** je Stadt.

**Wichtig:** Es muss der Datumsfilter auf **beiden** Spalten weg — auf der
Faktentabelle *und* auf der Dimension. Sonst bleibt der Filter stehen, das
Measure findet nicht den Anfang, sondern den aktuellen Punkt (Ergebnis: eine
flache Linie bei 100) oder gar nichts.

```dax
Erster Snapshot mit Preis =
CALCULATE (
    MIN ( fct[snapshot_date] ),
    REMOVEFILTERS ( fct[snapshot_date] ),
    REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
    fct[is_entire_home] = TRUE (),
    fct[has_price] = TRUE (),
    fct[is_price_outlier] = FALSE ()
)

Median Startpreis =
CALCULATE (
    [Median Nachtpreis],
    REMOVEFILTERS ( fct[snapshot_date] ),
    REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
    fct[snapshot_date] = [Erster Snapshot mit Preis]
)
```

**Die Stadt bleibt erhalten.** `REMOVEFILTERS` wirkt hier nur auf die
Datums-Spalten — der Filter aus der Legende (`city`) bleibt bestehen. Deshalb
bekommt jede Stadt ihren eigenen Startwert.

---

## 4. Der Index — das Herzstück

```dax
Index Nachtpreis =
VAR Start = [Median Startpreis]
RETURN
    DIVIDE ( [Median Nachtpreis], Start ) * 100
```

**Ergebnis:** Berlin startet bei 100 und endet bei 238,5; München startet bei 100
und endet bei 263,2. Beide Linien beginnen auf gleicher Höhe — damit ist der
Vergleich trotz 5 Jahren Unterschied fair.

---

## 4b. WICHTIG: `snapshot_date` ist Text, nicht Datum

Der Export schreibt ISO-Daten (`2015-09-01`). Power BI mit **deutschem
Gebietsschema** erwartet `01.09.2015` und erkennt die ISO-Form **nicht** — die
Spalte bleibt **Text**. Dann scheitert jeder Vergleich mit `DATE(...)`:

> DAX-Vergleichsvorgänge unterstützen keine Vergleiche zwischen Werten des Typs
> Text und Date.

### Sofortlösung: mit Text vergleichen

```dax
Median Startpreis =
VAR Stadt = SELECTEDVALUE ( mart_powerbi_report_schlank[city] )
VAR StartDatum =
    SWITCH ( Stadt,
        "Berlin",   "2015-09-01",
        "Muenchen", "2020-05-24"
    )
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
        REMOVEFILTERS ( mart_powerbi_report_schlank[snapshot_date] ),
        mart_powerbi_report_schlank[snapshot_date] = StartDatum
    )
```

ISO-Text sortiert korrekt (`2015` < `2020`), also funktioniert auch `MIN` auf
der Textspalte.

### Saubere Lösung: Typen in Power Query setzen

```m
= Table.TransformColumns(Ist, {
    {"snapshot_date",    each Date.FromText(_, [Format="yyyy-MM-dd"]), type date},
    {"last_review_date", each Date.FromText(_, [Format="yyyy-MM-dd"]), type date}
})
```

Das Gebietsschema ist **egal** — `2015-09-01` ist eindeutig (vierstelliges Jahr
vorn). Deutsch (Deutschland) kannst du eingestellt lassen. Das Format
`yyyy-MM-dd` wird fest vorgegeben, damit die Erkennung nicht vom Gebietsschema
abhängt.

Einfacher Weg ohne Formel: Spaltenkopf → **Rechte Maustaste → Typ ändern →
Datum**. Das genügt bei diesem Format.

**In beiden Tabellen** anwenden — `mart_powerbi_report_schlank` **und**
`dim_snapshot`. Sonst lässt sich die Beziehung nicht mehr herstellen
(Text ↔ Datum).

### Nebenbei prüfen

Sind `has_price`, `is_entire_home`, `is_price_outlier` vom Typ **True/False**?
Bei deutschem Gebietsschema liest Power BI `true`/`false` unter Umständen als
Text — dann scheitert `= TRUE ()` genauso. Im Feldbereich am Häkchen-Symbol
erkennbar.

---

## 5. Zusatz-Measures für die Karten

```dax
Zeitraum in Jahren =
VAR Erster = [Erster Snapshot mit Preis]
VAR Letzter =
    CALCULATE (
        MAX ( fct[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot ),
        fct[is_entire_home] = TRUE (),
        fct[has_price] = TRUE (),
        fct[is_price_outlier] = FALSE ()
    )
RETURN
    DIVIDE ( Letzter - Erster, 365.25 )

Preiswachstum gesamt % =
DIVIDE ( [Median Nachtpreis], [Median Startpreis] ) - 1

Preiswachstum pro Jahr =
VAR Jahre = [Zeitraum in Jahren]
RETURN
    IF ( Jahre > 0, ( [Median Nachtpreis] / [Median Startpreis] ) ^ ( 1 / Jahre ) - 1 )
```

### Kontrollwerte (Sept 2026 als Endpunkt)

| Stadt | Zeitraum | gesamt | **pro Jahr** |
| --- | ---: | ---: | ---: |
| Berlin | 11,05 Jahre | +138,5 % | **8,18 %** |
| München | 6,33 Jahre | +163,2 % | **16,51 %** |

### Kontrollwerte (Juni 2026 als Endpunkt, ohne Wiesn-Effekt)

| Stadt | Zeitraum | gesamt | **pro Jahr** |
| --- | ---: | ---: | ---: |
| Berlin | 10,82 Jahre | +138,5 % | **8,37 %** |
| München | 6,10 Jahre | +87,4 % | **10,85 %** |

---

## 6. Visual einrichten

**Liniendiagramm** (nicht Balken — eine Zeitreihe ist eine Linie):

- **X-Achse:** `dim_snapshot[snapshot_date]` — **nur Spalten, nie ein Measure**
- **Y-Achse:** `Index Nachtpreis` — **nur Measures, nie eine Spalte**
- **Legende:** `fct[city]`
- **Sekundärachse:** aus
- **Datenbeschriftung:** an (nur 7 Punkte)
- **Referenzlinie:** bei 100 einziehen (Startniveau)

### Wenn nichts angezeigt wird — Prüfliste

1. **Achsen vertauscht?** Das häufigste Problem: Ein Measure auf der X-Achse
   rendert Power BI nicht. `Index Nachtpreis` gehört auf die **Y-Achse**.
2. **Basis-Measure testen:** Eine Karte mit nur `Median Nachtpreis` anlegen.
   Bleibt sie leer, liegt der Fehler im Basis-Measure, nicht im Index.
3. **`Median Startpreis` testen:** Eine Karte mit nur diesem Measure. Sie muss
   je Stadt 65 (Berlin) bzw. 95 (München) zeigen. Zeigt sie leer, ist der
   Datumsfilter nicht aufgehoben (siehe Abschnitt 3).
4. **Beziehung aktiv?** `fct[snapshot_date]` → `dim_snapshot[snapshot_date]`
   muss aktiv und einfach gerichtet sein.
5. **`dim_snapshot[snapshot_date]` als Datum?** Nicht als Text. Sonst findet
   `MIN` nicht den richtigen Anfang.

### Damit die Lücken nicht stören

X-Achse → **„Elemente ohne Daten anzeigen"** abschalten. Sonst zieht Power BI
2025-12 und 2026-03 als leere Kategorien mit.

### Warum die Linie bei 2015 bzw. 2020 beginnt

Berlin hat keinen Preis-Stand zwischen 2015 und 2026. Die Linie springt also von
2015 direkt auf 2026. Das ist die Datenlage, nicht ein Fehler. Wer das glätten
will, kann die X-Achse auf **„Kategorie"** stellen — dann liegen die Messpunkte
gleich weit auseinander (ehrlicher für „Veränderung je Messpunkt", weniger
ehrlich für „Veränderung über Zeit").

---

## 7. Wichtiger Hinweis zur Aussage

Die Karten vergleichen **verschiedene Zeiträume**:

- Berlin: 2015 → 2026 = **10,8 Jahre**
- München: 2020 → 2026 = **6,1 Jahre**

Deshalb wächst Berlin **in Prozentpunkten** schneller (+138 % gegen +87 %), aber
**pro Jahr** wächst **München** schneller (10,9 % gegen 8,4 %; mit September sogar
16,5 % gegen 8,2 %).

**Ein Titel „Berlin wächst schneller" ist damit nicht haltbar.** Besser:

> „München bleibt teurer — beide Städte legen deutlich zu"
> oder: „München wächst pro Jahr schneller"

---

## 8. Zwei Datenhinweise (Ehrlichkeit)

1. **September-München ist Wiesn-verzerrt.** Der Sprung auf 250 € fällt auf den
   23.09. mitten im Oktoberfest. Für eine langfristige Wachstumsaussage ist der
   **Juni-Stand** (178 €) belastbarer. Am besten beide Endpunkte ausweisen.

2. **Die Quellen sind nicht identisch.** Berlin 2015 und München 2020 stammen aus
   älteren GitHub-Snapshots (100 % Preis-Abdeckung), die 2026er Stände aus
   Inside-Airbnb-visualisations (66–69 %). Die Preisbasis ist also nicht
   vollständig vergleichbar — der Trend ist aussagekräftig, die exakte
   Prozentzahl nur bedingt.

---

## 9. Prüfliste

- [ ] `Index Nachtpreis` auf der Y-Achse, `city` als Legende.
- [ ] X-Achse = `snapshot_date` (kontinuierlich).
- [ ] „Elemente ohne Daten anzeigen" aus.
- [ ] Titel korrigiert (München wächst pro Jahr schneller).
- [ ] Großes Visual vom Slicer ausgenommen (Format → Interaktionen bearbeiten → Keine).
- [ ] Beide Endpunkte (Juni und September) ausweisen, weil September Wiesn-verzerrt ist.
