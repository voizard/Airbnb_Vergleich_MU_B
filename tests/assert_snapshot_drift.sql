{{ config(severity='warn') }}

-- Singular Test (Warnung): starke Schwankungen der Zeilenzahl zwischen zwei
-- Snapshots derselben Stadt deuten auf Scraping-Lücken in der Quelle hin.
-- Bekannter Fall: Berlin 2026-03-28 hat rund 59 Prozent weniger Zeilen als der
-- Vorgänger-Snapshot. Der Test bleibt bewusst auf severity warn, damit der
-- Build grün bleibt, die Auffälligkeit aber sichtbar wird.
with zahlen as (

    select
        city,
        snapshot_date,
        count(*) as listing_count,
        lag(count(*)) over (
            partition by city order by snapshot_date
        ) as previous_count
    from {{ ref('stg_airbnb__listings') }}
    group by 1, 2

)

select
    city,
    snapshot_date,
    listing_count,
    previous_count,
    round((listing_count - previous_count) * 1.0 / previous_count, 4) as abweichung
from zahlen
where previous_count is not null
  and abs(listing_count - previous_count) * 1.0 / previous_count
      > {{ var('snapshot_drift_schwelle') }}
