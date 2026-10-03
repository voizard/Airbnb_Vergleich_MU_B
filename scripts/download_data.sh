#!/usr/bin/env bash
# Lädt die für dieses Projekt verwendeten Inside-Airbnb-Snapshots
# (visualisations/listings.csv) nach ${ZIEL:-../airbnb/raw}.
#
# Die historische Berlin-Datei (2015-09) ist NICHT Teil dieses Skripts; sie
# stammt aus dem Inside-Airbnb-Archiv und wird nur für den Zeitvergleich
# gebraucht. Fehlt sie, lädt load_raw.py die übrigen Snapshots trotzdem.
set -euo pipefail

ZIEL="${ZIEL:-$(dirname "$0")/../../airbnb/raw}"
BASE="https://data.insideairbnb.com/germany"

# Stadt|Bundesland-Kürzel|Datum
SNAPSHOTS=(
  "berlin|be|2025-12-27"
  "berlin|be|2026-03-28"
  "berlin|be|2026-06-26"
  "munich|bv|2025-12-29"
  "munich|bv|2026-03-30"
  "munich|bv|2026-06-29"
)

mkdir -p "$ZIEL/vis" "$ZIEL/berlin" "$ZIEL/munich"

for eintrag in "${SNAPSHOTS[@]}"; do
  IFS="|" read -r stadt land datum <<< "$eintrag"
  datei="$ZIEL/vis/${stadt}-${datum}-listings.csv"
  if [ -s "$datei" ]; then
    echo "vorhanden: $datei"
    continue
  fi
  url="$BASE/$land/$stadt/$datum/visualisations/listings.csv"
  echo "lade: $url"
  curl -fsSL --retry 3 --retry-delay 5 -o "$datei" "$url"
  echo "  -> $datei ($(wc -l < "$datei") Zeilen)"
  sleep 1
done

for stadt in berlin munich; do
  datei="$ZIEL/$stadt/neighbourhoods.csv"
  if [ -s "$datei" ]; then
    echo "vorhanden: $datei"
    continue
  fi
  # Datum der Bezirksliste ist unkritisch; die Liste ändert sich selten.
  url="$BASE/$( [ "$stadt" = berlin ] && echo be || echo bv )/$stadt/2026-06-26/visualisations/neighbourhoods.csv"
  echo "lade: $url"
  curl -fsSL --retry 3 --retry-delay 5 -o "$datei" "$url" || echo "  (übersprungen: $stadt/neighbourhoods.csv nicht verfügbar)"
done

echo
echo "Fertig. Rohdaten unter: $ZIEL"
echo "Nächster Schritt: python3 scripts/load_raw.py --raw-dir $ZIEL"
