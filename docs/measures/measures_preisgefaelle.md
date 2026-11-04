# Preisgefälle Juni → September 2026

Stand 2026-11-04 · Projekt: dbt-airbnb

**Ziel:** Der Bericht enthält **alle** Snapshot-Stände (September inklusive), damit
sich das Preisgefälle zwischen den Städten und Bezirken analysieren lässt.
Die September-Daten verzerren nichts, solange der Vergleich **je Stück** läuft —
also Juni gegen September, nicht „alles gepoolt".

---

## 1. Warum der September drin bleibt

Gepoolt über alle Stände zieht September das Bild nach oben:

| | mit September | ohne September |
| --- | ---: | ---: |
| Berlin, Median (ganze Unterk.) | 94 € | 75 € |
| München, Median (ganze Unterk.) | 149 € | 127 € |

Für das **Gefälle** ist September aber der Kern: Es ist der einzige Stand nach
der Sommersaison und zeigt den Wiesn-Effekt in München.

---

## 2. Das Preisgefälle (ganze Unterkünfte, Median je Inserat)

| Stadt | Juni 2026 | September 2026 | Delta | Veränderung |
| --- | ---: | ---: | ---: | ---: |
| Berlin | 155 € | 155 € | 0 € | 0,0 % |
| München | 178 € | 250 € | **+72 €** | **+40,4 %** |

**Kernbefund:** Das Gefälle zwischen den Städten wächst von **23 €** (Juni) auf
**95 €** (September).

### Stärkste Bezirke in München (Juni → September)

| Bezirk | Juni | September | Delta |
| --- | ---: | ---: | ---: |
| Ludwigsvorstadt-Isarvorstadt | 210,5 € | 320,0 € | **+109,5** |
| Feldmoching-Hasenbergl | 135,5 € | 237,5 € | +102,0 |
| Hadern | 138,5 € | 240,0 € | +101,5 |
| Schwabing-West | 186,5 € | 271,5 € | +85,0 |
| Pasing-Obermenzing | 131,0 € | 215,5 € | +84,5 |
| Sendling-Westpark | 175,5 € | 258,0 € | +82,5 |
| Bogenhausen | 179,5 € | 260,0 € | +80,5 |
| Neuhausen-Nymphenburg | 160,0 € | 240,0 € | +80,0 |

### Berlin bleibt flach

| Bezirk | Juni | September | Delta |
| --- | ---: | ---: | ---: |
| Charlottenburg-Wilm. | 131 € | 144 € | +13 |
| Marzahn - Hellersdorf | 122 € | 130 € | +8 |
| Treptow - Köpenick | 124 € | 131 € | +7 |

Kein Berliner Bezirk bewegt sich mehr als +13 €.

**Einordnung (Hypothese, nicht bewiesen):** Der September-Snapshot München fällt
auf den **23.09.** — mitten im Oktoberfest. Die Bezirke an der Theresienwiese
(Ludwigsvorstadt, Schwanthalerhöhe) springen am stärksten. Das ist ein starkes
Story-Element, aber als Hypothese kennzeichnen: Der Snapshot liefert nur einen
Zeitpunkt, keinen Kausalnachweis.

---

## 3. Measures für das Dumbbell-Visual

Auf der Faktentabelle, **ohne** feste Daten — ein neuer Snapshot läuft automatisch mit:

```dax
Median Nachtpreis =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    fct[is_entire_home] = TRUE (),
    fct[has_price] = TRUE (),
    fct[is_price_outlier] = FALSE ()
)

Median Juni 2026 =
CALCULATE (
    [Median Nachtpreis],
    REMOVEFILTERS ( dim_snapshot ),
    dim_snapshot[snapshot_month] = 6,
    dim_snapshot[snapshot_year] = 2026
)

Median September 2026 =
CALCULATE (
    [Median Nachtpreis],
    REMOVEFILTERS ( dim_snapshot ),
    dim_snapshot[snapshot_month] = 9,
    dim_snapshot[snapshot_year] = 2026
)

Preisgefälle € = [Median September 2026] - [Median Juni 2026]

Preisgefälle % = DIVIDE ( [Preisgefälle €], [Median Juni 2026] )
```

### Dynamisch statt fest (letzter gegen vorletzten Snapshot)

```dax
Letzter Snapshot =
CALCULATE ( MAX ( dim_snapshot[snapshot_date] ), REMOVEFILTERS ( dim_snapshot ) )

Vorletzter Snapshot =
VAR Letzter = [Letzter Snapshot]
RETURN
    CALCULATE (
        MAX ( dim_snapshot[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot ),
        dim_snapshot[snapshot_date] < Letzter
    )

Median letzter Snapshot =
CALCULATE ( [Median Nachtpreis],
    REMOVEFILTERS ( dim_snapshot ),
    dim_snapshot[snapshot_date] = [Letzter Snapshot] )

Median vorletzter Snapshot =
CALCULATE ( [Median Nachtpreis],
    REMOVEFILTERS ( dim_snapshot ),
    dim_snapshot[snapshot_date] = [Vorletzter Snapshot] )

Preisgefälle dynamisch € =
[Median letzter Snapshot] - [Median vorletzter Snapshot]
```

**Achtung bei der dynamischen Variante:** Berlin und München haben je zwei
Junistände (26.06. / 29.06.) und zwei Septemberstände. „Letzter Snapshot" wäre
dann der 23.09. (München) — für Berlin gäbe es keinen Wert am selben Tag.
Deshalb beim Dumbbell die **festen Juni/September-Measures** nehmen; die
dynamische Variante nur, wenn eine Stadt gefiltert ist.

---

## 4. Visual: Dumbbell Bar Chart

- **Kategorie:** `fct[district]`
- **Werte:** `Median Juni 2026` und `Median September 2026`
- **Tooltip:** `Preisgefälle %`, `Preis-Abdeckung %`
- **Slicer:** `dim_snapshot[snapshot_label]` (nicht die Faktentabelle)
- **city-Slicer** auf `fct[city]` — Berlin und München getrennt betrachten

---

## 5. Prüfliste

- [ ] `dim_snapshot` geladen, `snapshot_date` als **Datum / Deutsch**.
- [ ] Beziehung `dim_snapshot[snapshot_date]` (1) → `fct[snapshot_date]` (n).
- [ ] Slicer auf `dim_snapshot`, nicht auf `fct[snapshot_date]`.
- [ ] `snapshot_label` nach `snapshot_sort` sortieren.
- [ ] Keine `DATE ( … )`-Literale in den Measures.
- [ ] September-Daten bleiben drin — sie sind die Vergleichsbasis.
