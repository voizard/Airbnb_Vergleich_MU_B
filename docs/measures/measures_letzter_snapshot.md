# Measures: „letzter Snapshot" — unabhängig vom Slicer

Stand 2026-11-04 · Projekt: dbt-airbnb
Tabellen: `fct` = `mart_powerbi_report_schlank`, `dim_snapshot` = Snapshot-Dimension.

**Zweck:** Die vier kleinen Kacheln (Inserate, Preis-Abdeckung) sollen immer den
**jüngsten** Snapshot je Stadt zeigen — egal was im Slicer steht. Damit passen sie
zur Fußnote „Stand September 2026", auch wenn man oben auf Juni schaltet.

---

## Die Falle (heute zweimal passiert)

Der Slicer hängt an **`dim_snapshot[snapshot_date]`**. Deshalb reicht
`REMOVEFILTERS ( fct[snapshot_date] )` **nicht** — der Filter kommt über die
Beziehung von der Dimension. Es müssen **beide** Datums-Spalten aufgehoben werden:

```dax
REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
REMOVEFILTERS ( fct[snapshot_date] )
```

Fehlt einer davon, liefert das Measure **BLANK** (Kachel leer) oder den falschen
Stand. Die **Stadt** bleibt dabei erhalten — `REMOVEFILTERS` wirkt nur auf die
Datums-Spalten, nicht auf den Filter der Kachel.

---

## 1. Jüngster Snapshot je Stadt

```dax
Letzter Snapshot =
VAR Juengster =
    CALCULATE (
        MAX ( fct[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot ),
        REMOVEFILTERS ( fct[snapshot_date] )
    )
RETURN
    Juengster
```

**Ergebnis:** Berlin 19.09.2026 · München 23.09.2026

---

## 2. Inserate (letzter Snapshot)

Zählt ganze Unterkünfte **mit** Preis, ohne Ausreißer.

```dax
Inserate letzter Snapshot =
VAR Juengster = [Letzter Snapshot]
RETURN
    CALCULATE (
        COUNTROWS ( fct ),
        REMOVEFILTERS ( dim_snapshot ),
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] = Juengster,
        fct[is_entire_home] = TRUE (),
        fct[has_price] = TRUE (),
        fct[is_price_outlier] = FALSE ()
    )
```

**Ergebnis:** Berlin **5.840** · München **3.138**

### Variante: alle Unterkünfte (nicht nur ganze)

Falls die Kachel „Inserate" alle Zimmertypen meinen soll — dann die Zeile
`fct[is_entire_home] = TRUE (),` streichen:

| Stadt | ganze Unterkünfte | alle Zimmertypen |
| --- | ---: | ---: |
| Berlin | **5.840** | 8.130 |
| München | **3.138** | 4.972 |

Der Screenshot zeigt 5,84 Tsd. und 3,14 Tsd. → es ist die **ganze-Unterkünfte**-
Variante.

---

## 3. Preis-Abdeckung (letzter Snapshot)

```dax
Preis-Abdeckung letzter Snapshot % =
VAR Juengster = [Letzter Snapshot]
VAR Basis =
    CALCULATE (
        COUNTROWS ( fct ),
        REMOVEFILTERS ( dim_snapshot ),
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] = Juengster,
        fct[is_entire_home] = TRUE ()
    )
VAR MitPreis =
    CALCULATE (
        COUNTROWS ( fct ),
        REMOVEFILTERS ( dim_snapshot ),
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] = Juengster,
        fct[is_entire_home] = TRUE (),
        fct[has_price] = TRUE (),
        fct[is_price_outlier] = FALSE ()
    )
RETURN
    DIVIDE ( MitPreis, Basis )
```

Format der Kachel: **Prozent, 0 Dezimalstellen** (Feld → Format → Prozent).

**Ergebnis:** Berlin **69,2 %** (5.840 / 8.446) · München **62,9 %** (3.138 / 4.988)

---

## 4. Fußnote dynamisch (statt statischer Text)

Damit sich die Fußnote nicht widerspricht, wenn ein neuer Snapshot dazukommt:

```dax
Fussnote =
"Stand " & FORMAT ( [Letzter Snapshot], "MMMM JJJJ" ) &
" — Median je Inserat, nur ganze Unterkünfte"
```

Ergibt „Stand September 2026 …". Als **Karte** mit diesem Measure einbauen — dann
steht dort nie ein veraltetes Datum.

---

## 5. Prüfliste

- [ ] **Beide** `REMOVEFILTERS` drin — `dim_snapshot` **und** `fct[snapshot_date]`.
- [ ] Kachel `Inserate letzter Snapshot` zeigt **5.840** / **3.138**.
- [ ] Kachel `Preis-Abdeckung letzter Snapshot %` zeigt **69 %** / **63 %**.
- [ ] Slicer auf **Juni** stellen und prüfen: Die vier kleinen Kacheln **ändern
      sich nicht**. Die großen Preis-Kacheln dürfen reagieren.
- [ ] Fußnote auf „Stand September 2026" — oder als Measure (Abschnitt 4).

---

## 6. Warum die kleinen Kacheln vorher reagierten

Sie hatten kein eigenes Measure, sondern nutzten die Spalte `has_price` direkt
(implizite Aggregation). Damit griff der Slicer voll durch. Erst mit
`CALCULATE` + `REMOVEFILTERS` bekommt die Kachel einen **eigenen** Filterkontext.

**Wichtig:** Die Kachel muss das **Measure** als Wert haben, nicht die Spalte
`has_price`. Sonst bleibt sie slicer-abhängig.
