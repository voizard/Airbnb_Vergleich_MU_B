-- Mart: Preisentwicklung je Bezirk über die Snapshots.
-- Korn: eine Zeile je Stadt, Bezirk und Snapshot mit Medianpreis und Veränderung
-- zum jeweils vorherigen Snapshot.
with kennzahlen as (

    select
        city,
        district,
        snapshot_date,
        median_price_eur,
        listing_count,
        listings_with_price
    from {{ ref('mart_district_kpis') }}
    where median_price_eur is not null

),

zeitreihe as (

    select
        *,
        lag(median_price_eur) over w as previous_median_price_eur,
        lag(snapshot_date)    over w as previous_snapshot_date
    from kennzahlen
    window w as (partition by city, district order by snapshot_date)

)

select
    *,
    round(median_price_eur - previous_median_price_eur, 2)                       as price_change_eur,
    round(
        (median_price_eur - previous_median_price_eur)
        / nullif(previous_median_price_eur, 0), 4
    )                                                                            as price_change_share
from zeitreihe
