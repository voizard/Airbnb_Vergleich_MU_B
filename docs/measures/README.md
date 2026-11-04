# Power-BI-Measures

Sammlung der DAX-Measures für den Bericht. Je Datei ein Thema. Die Measures
arbeiten auf `mart_powerbi_report_schlank` (`fct`) und `dim_snapshot`.

**Voraussetzung für alle:** `snapshot_date` muss in **beiden** Tabellen vom Typ
**Datum** sein. Sonst scheitert jeder Datumsvergleich mit „Vergleiche zwischen
Text und Date" — siehe README, Abschnitt *Fallen beim Power-Query-Import*.

---

## Übersicht

| Datei | Thema | Stand |
| --- | --- | --- |
| `measures_median_preis.md` | Median-Nachtpreis (Bezirk, Stadt, Trend) — Grundregel „nie SUM auf Preise" | aktuell |
| `measures_jahresindex.md` | Wachstum pro Jahr; feste, Wiesn-bereinigte Endpunkte | aktuell |
| `measures_preisgefaelle.md` | Preisgefälle Juni → September, je Stück statt gepoolt | aktuell |
| `measures_slicer_fest.md` | Refresh-feste Measures ohne feste Daten | aktuell |
| `measures_letzter_snapshot.md` | Kacheln fest am jüngsten Snapshot (slicer-unabhängig) | nicht im Bericht verwendet |
| `measures_juni_2026.md` | Trendkarten auf Juni umstellen | überholt |
| `measures_preisindex.md` | Index mit Start = 100 | überholt → `measures_jahresindex.md` |

### Was der Bericht tatsächlich nutzt

- **Seite 1 „Preisentwicklung"** — `measures_median_preis.md` (Median, ganze
  Unterkünfte, ohne Ausreißer über 1.000 €), Stand **Juni 2026**.
- **Seite 2 „Verfügbarkeit"** — dieselbe Basis, zusätzlich
  `measures_preisgefaelle.md`.
- **Seite 3 „Lagen"** — Bezirks-Aggregate aus `measures_median_preis.md`.

### Warum zwei Dateien überholt sind

- `measures_preisindex.md` schlug einen **Index mit Start = 100** als Linie vor.
  Der funktioniert nicht als Zeitreihe, weil Berlin (ab 2015) und München (ab
  2020) verschieden lange Zeiträume haben — Berlin endet allein deshalb höher.
  Ersetzt durch `measures_jahresindex.md` (Wachstum **pro Jahr**).
- `measures_juni_2026.md` beschreibt einen Zwischenstand, als die Trendkarten
  noch am September hingen. Mit dem Juni-Fix erledigt.

Beide bleiben als Nachweis der Herleitung liegen, sind aber **nicht** zu
verwenden.

---

## Grundregeln (gelten überall)

1. **Nie `SUM` auf Preise.** Immer `MEDIAN` — ein Ausreißer verschiebt sonst den
   ganzen Bezirk.
2. **`REMOVEFILTERS` immer auf beide Datums-Spalten** — `dim_snapshot[snapshot_date]`
   **und** `fct[snapshot_date]`. Der Slicer hängt an der Dimension; hebt man nur
   die Faktentabelle auf, bleibt der Filter stehen und das Measure liefert BLANK.
3. **Zahlen in deutscher Schreibweise** (Dezimalkomma) — der Export schreibt sie so,
   Power BI liest mit Gebietsschema Deutsch.
4. **Wiesn-Effekt beachten.** München springt im September auf 250 € (Snapshot
   23.09., mitten im Oktoberfest). Für Wachstumsaussagen den **Juni-Stand**
   (178 €) verwenden, sonst verzerrt der Saisoneffekt das Ergebnis.
