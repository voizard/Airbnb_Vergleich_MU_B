# Jahres-Index — Measures für den Preisverlauf

Stand 2026-11-04 · Projekt: dbt-airbnb
Tabellen: `mart_powerbi_report_schlank` (Fakt), `dim_snapshot` (Zeitdimension).

**Voraussetzung:** `snapshot_date` muss in **beiden** Tabellen vom Typ **Datum**
sein (Kalender-Symbol im Feldbereich, nicht „ABC"). Sonst scheitert jede
Datums-Rechnung mit „Vergleiche zwischen Text und Date".

---

## 1. Basis

```dax
Median-Nachtpreis =
CALCULATE (
    MEDIAN ( mart_powerbi_report_schlank[price_eur] ),
    mart_powerbi_report_schlank[is_entire_home] = TRUE (),
    mart_powerbi_report_schlank[has_price] = TRUE (),
    mart_powerbi_report_schlank[is_price_outlier] = FALSE ()
)
```

---

## 2. Startpunkt je Stadt — dynamisch

Sucht selbst den ersten Snapshot mit Preis. `REMOVEFILTERS` muss auf **beide**
Datums-Spalten wirken (Fakt **und** Dimension) — sonst bleibt der Achsenfilter
stehen und das Measure liefert leer.

```dax
Median-Nachtpreis Erster Snapshot =
VAR Erster =
    CALCULATE (
        MIN ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
        mart_powerbi_report_schlank[is_entire_home] = TRUE (),
        mart_powerbi_report_schlank[has_price] = TRUE (),
        mart_powerbi_report_schlank[is_price_outlier] = FALSE ()
    )
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
        mart_powerbi_report_schlank[snapshot_date] = Erster
    )
```

**Ergebnis:** Berlin 65 € (Sept 2015), München 95 € (Mai 2020).

---

## 3. Zeitraum bis zum aktuellen Achsenpunkt

```dax
Zeitraum in Jahren =
VAR Erster =
    CALCULATE (
        MIN ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
        mart_powerbi_report_schlank[is_entire_home] = TRUE (),
        mart_powerbi_report_schlank[has_price] = TRUE (),
        mart_powerbi_report_schlank[is_price_outlier] = FALSE ()
    )
VAR Aktuell = MAX ( mart_powerbi_report_schlank[snapshot_date] )
RETURN
    DIVIDE ( Aktuell - Erster, 365.25 )
```

**Das** ist `[Zeitraum in Jahren]` — die Tage zwischen erstem Messpunkt und dem
jeweils betrachteten Punkt, geteilt durch 365,25.

---

## 4. Der Jahres-Index — das Hauptmeasure

```dax
Index pro Jahr =
VAR Jahre = [Zeitraum in Jahren]
VAR Start = [Median-Nachtpreis Erster Snapshot]
VAR Jetzt = [Median-Nachtpreis]
RETURN
    IF (
        Jahre <= 0 || ISBLANK ( Jetzt ),
        BLANK (),
        DIVIDE ( Jetzt, Start ) ^ ( 1 / Jahre ) * 100
    )
```

**Startpunkt ergibt 100.** Jeder weitere Punkt zeigt, wo die Stadt stünde, wenn
sie gleichmäßig gewachsen wäre — damit sind die verschiedenen Startjahre
(Berlin 2015, München 2020) vergleichbar.

### Kontrollwerte

| Stadt | Punkt | Preis | Index pro Jahr |
| --- | --- | ---: | ---: |
| Berlin | Sept 2015 | 65 € | **100,00** |
| Berlin | Juni 2026 | 155 € | **108,38** |
| Berlin | Sept 2026 | 155 € | **108,18** |
| München | Mai 2020 | 95 € | **100,00** |
| München | März 2026 | 182 € | **111,82** |
| München | Juni 2026 | 178 € | **110,85** |
| München | Sept 2026 | 250 € | **116,51** ← Wiesn, siehe unten |

**Lesart:** Berlin wuchs mit 8,2 % pro Jahr, München mit 10,9 %. Der Jahres-Index
zeigt das korrekt — anders als der Gesamt-Index, wo Berlin wegen des längeren
Zeitraums oben lag.

---

## 5. Wiesn-Problem: fester Endpunkt je Stadt

Münchens September-Wert (23.09.) fällt mitten ins Oktoberfest und ist kein
Preisniveau, sondern ein Saisoneffekt. Für Wachstumsaussagen deshalb **feste,
saisonverträgliche Endpunkte** verwenden:

```dax
Median-Nachtpreis Endwert =
VAR Stadt = SELECTEDVALUE ( mart_powerbi_report_schlank[city] )
VAR EndDatum =
    SWITCH (
        Stadt,
        "Berlin",   DATE ( 2026, 9, 19 ),   -- gleiche Saison wie Start
        "Muenchen", DATE ( 2026, 6, 29 )    -- Vorsaison, ohne Wiesn
    )
RETURN
    CALCULATE (
        [Median-Nachtpreis],
        REMOVEFILTERS ( mart_powerbi_report_schlank[snapshot_date] ),
        REMOVEFILTERS ( dim_snapshot[snapshot_date] ),
        mart_powerbi_report_schlank[snapshot_date] = EndDatum
    )

Preiswachstum pro Jahr (bereinigt) =
VAR Start = [Median-Nachtpreis Erster Snapshot]
VAR Ende = [Median-Nachtpreis Endwert]
VAR Jahre =
    SWITCH (
        SELECTEDVALUE ( mart_powerbi_report_schlank[city] ),
        "Berlin",   11.05,
        "Muenchen",  6.10
    )
RETURN
    IF (
        ISBLANK ( Start ) || ISBLANK ( Ende ),
        BLANK (),
        DIVIDE ( Ende, Start ) ^ ( 1 / Jahre ) - 1
    )
```

### Ergebnis (Wiesn-bereinigt)

| Stadt | Zeitraum | Start → Ende | pro Jahr |
| --- | ---: | ---: | ---: |
| Berlin | 11,05 Jahre | 65 € → 155 € | **+8,18 %** |
| München | 6,10 Jahre | 95 € → 178 € | **+10,85 %** |

**München wächst pro Jahr schneller.** Der Titel „Berlin wächst schneller" ist
damit widerlegt.

---

## 6. Visual einrichten

**Liniendiagramm:**

- **X-Achse:** `dim_snapshot[snapshot_label]`
  → vorher in der Datenansicht: `snapshot_label` markieren → **Spaltentools →
  Nach Spalte sortieren → `snapshot_sort`**. Dann läuft die Achse chronologisch.
- **Y-Achse:** `Index pro Jahr`
- **Legende:** `city`
- **Y-Achsentitel:** „Index pro Jahr (Start = 100)"
- **Datenbeschriftung:** an

### Lücke und Ausreißer

- **Dez 2025 / März 2026 Berlin:** keine Preise → Lücke. X-Achse →
  „Elemente ohne Daten anzeigen" abschalten.
- **Sept 2026 München:** Wiesn-Ausreißer (116,5). Entweder ausblenden oder als
  eigenen Befund stehen lassen.

---

## 7. Notiz für den Bericht

> Nur Messpunkte aus den Snapshots. Zwischen 2016 und 2025 liegen keine Daten
> vor. Der September-Wert München (23.09.2026) fällt ins Oktoberfest und ist ein
> Saisoneffekt, kein Preisniveau. Wachstumsaussagen nutzen daher den Juni-Stand.

---

## 8. Prüfliste

- [ ] `snapshot_date` in **beiden** Tabellen Typ **Datum**.
- [ ] Karte mit `Median-Nachtpreis Erster Snapshot` → muss **65** (Berlin) und **95** (München) zeigen.
- [ ] Karte mit `Preiswachstum pro Jahr (bereinigt)` → **8,18 %** bzw. **10,85 %**.
- [ ] `snapshot_label` nach `snapshot_sort` sortiert.
- [ ] Y-Achse = `Index pro Jahr` (nicht der Rohpreis).
- [ ] Titel korrigiert: „München bleibt teurer — München wächst pro Jahr schneller".
