# Measures: Trendkarten auf JUNI 2026 umstellen

Stand 2026-11-04 · Projekt: dbt-airbnb (`mart_powerbi_report_schlank`)

## Der Befund

Die beiden großen Karten („Entwicklung Nachtpreis") vergleichen **erster Snapshot →
letzter Snapshot**. Der letzte Snapshot ist **September 2026** — deshalb steht dort
der September-Preis, obwohl der Slicer auf Juni steht. Ein Slicer kann das nicht
korrigieren, weil das Measure den jüngsten Snapshot selbst ermittelt.

| Karte | zeigt jetzt | soll zeigen (Juni) |
| --- | ---: | ---: |
| Berlin: 65 € → **155 €** | 155 € | 155 € *(zufällig gleich)* |
| München: 95 € → **250 €** | 250 € | **178 €** |

Wichtig: In **Berlin** sind Juni- und September-Median identisch (beide 155 €) —
dort fällt der Unterschied nicht auf. In **München** schon: 250 € (September)
gegen **178 €** (Juni).

---

## 1. Startwert (erster Snapshot) — bleibt wie er ist

```dax
Median-Nachtpreis Startwert =
VAR Erster =
    CALCULATE ( MIN ( fct[snapshot_date] ), REMOVEFILTERS ( fct[snapshot_date] ) )
RETURN
    CALCULATE (
        MEDIAN ( fct[price_eur] ),
        REMOVEFILTERS ( fct[snapshot_date] ),
        fct[snapshot_date] = Erster,
        fct[is_entire_home] = TRUE,
        fct[has_price] = TRUE,
        fct[is_price_outlier] = FALSE
    )
```

Ergebnis: Berlin 65 € (2015-09), München 95 € (2020-05).

## 2. Endwert auf JUNI 2026 festnageln — das ist die Änderung

```dax
Median-Nachtpreis Juni 2026 =
CALCULATE (
    MEDIAN ( fct[price_eur] ),
    REMOVEFILTERS ( fct[snapshot_date] ),
    fct[snapshot_date] >= DATE ( 2026, 6, 1 ),
    fct[snapshot_date] <= DATE ( 2026, 6, 30 ),
    fct[is_entire_home] = TRUE,
    fct[has_price] = TRUE,
    fct[is_price_outlier] = FALSE
)
```

Der Juni-Bereich 01.–30.06. deckt **beide** Städte ab (Berlin 26.06.,
München 29.06.) — ein festes Einzeldatum wäre falsch.

Ergebnis: Berlin **155 €**, München **178 €**.

## 3. Veränderung

```dax
Veränderung Startwert bis Juni % =
DIVIDE (
    [Median-Nachtpreis Juni 2026] - [Median-Nachtpreis Startwert],
    [Median-Nachtpreis Startwert]
)
```

Ergebnis: Berlin **+138,46 %** (65 → 155), München **+87,37 %** (95 → 178).

---

## 4. Wichtig: Datumstyp vorher reparieren

Dein Slicer zeigt zwei Formate gleichzeitig:

```
2026-06-29          <- Text
2026-09-19          <- Text
2026-09-23          <- Text
29.06.2026 00:00:00 <- echtes Datum
26.06.2026 00:00:00 <- echtes Datum
```

In einer Spalte kann nur **ein** Typ stehen. Zwei Formate heißen: es sind zwei
verschiedene Datenquellen im Modell (z. B. CSV **und** ODBC-Verbindung) oder zwei
Slicer übereinander. Solange das so ist, greift kein Datumsfilter zuverlässig —
und `DATE ( 2026, 6, 1 )` kann am Textvergleich scheitern.

**Zu tun:**
1. Modellansicht öffnen — welche Tabellen sind geladen? Dieselben Daten doppelt?
2. Überzählige Tabelle entfernen (CSV **oder** ODBC, nicht beides).
3. `snapshot_date` → Datentyp **Datum**, Gebietsschema **Deutsch (Deutschland)**.

**Übergangslösung, falls der Typ noch Text ist:** statt `DATE ( 2026, 6, 1 )`
mit Textgrenzen arbeiten — ISO-Text sortiert chronologisch korrekt:

```dax
fct[snapshot_date] >= "2026-06-01",
fct[snapshot_date] <= "2026-06-30",
```

---

## 5. Prüfliste

- [ ] Alle Measures durchsuchen nach `MAX ( fct[snapshot_date] )` — das ist der
      „jüngster Snapshot"-Griff. Ersetzen durch die Juni-Bedingung aus Abschnitt 2.
- [ ] `REMOVEFILTERS ( fct[snapshot_date] )` allein reicht nicht — danach muss
      die feste Datumsgrenze kommen, sonst bleibt der Filter wirkungslos.
- [ ] Fußnote („Stichtag 26. bzw. 29. Juni 2026") ist statischer Text — auf
      September ändern oder durch ein Measure ersetzen.
