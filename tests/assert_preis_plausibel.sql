-- Singular Test: Preise muessen plausibel sein.
-- Erfolgreich, wenn die Abfrage null Zeilen zurueckgibt.
-- Geprueft werden negative Preise (Datenfehler) und Null-Preise in der
-- Preisspalte der Marts (dort wird nur mit vorhandenen Preisen gerechnet).
with listings as (

    select * from {{ ref('fct_listing_snapshot') }}

)

select
    listing_snapshot_key,
    price_eur,
    'negativer Preis' as fehler
from listings
where price_eur < 0

union all

select
    district_key,
    median_price_eur,
    'Median ohne auswertbare Preise'
from {{ ref('mart_district_kpis') }}
where median_price_eur is null
  and listings_with_price > 0
