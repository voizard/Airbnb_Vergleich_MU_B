-- Dimension: Bezirkskennzahlen je Bezirk und Snapshot (148 Zeilen).
-- Korn: eine Zeile je Stadt, Bezirk und Snapshot-Datum.
-- Inhaltlich dieselben Kennzahlen wie mart_district_kpis, zusaetzlich der
-- Primaerschluessel district_snapshot_id (fuer Power BI) und die Veraenderung
-- zum naechsten frueheren Snapshot MIT Preis.
-- Preisgrenzen: Ausreisser oberhalb von var('max_plausibler_preis_eur') werden
-- aus den Preiskennzahlen ausgeschlossen, aber gezaehlt (district_price_outlier_count).
-- Die Kennzahlen sind nicht additiv: nie summieren, nur lesen.
with basis as (

    select * from {{ ref('fct_listing_snapshot') }}

),

kennzahlen as (

    select
        district_key,
        city,
        district,
        snapshot_date,

        count(*)                                                          as district_listing_count,
        count(*) filter (where is_entire_home)                            as district_entire_home_count,
        round(count(*) filter (where is_entire_home) * 1.0 / count(*), 4) as district_entire_home_share,

        count(*) filter (where has_price)                                 as district_listings_with_price,
        round(count(*) filter (where has_price) * 1.0 / count(*), 4)      as district_price_coverage_share,
        round(
            median(price_eur) filter (where has_price and not is_price_outlier), 2
        )                                                                 as district_median_price_eur,
        round(
            avg(price_eur) filter (where has_price and not is_price_outlier), 2
        )                                                                 as district_avg_price_eur,
        count(*) filter (where is_price_outlier)                          as district_price_outlier_count,

        round(avg(availability_365), 1)                                   as district_avg_availability_365,
        round(avg(reviews_ltm), 1)                                        as district_avg_reviews_ltm,

        count(distinct host_id)                                           as district_host_count,
        count(distinct host_id) filter (where is_commercial_host)         as district_commercial_host_count,
        round(
            count(distinct host_id) filter (where is_commercial_host) * 1.0
            / nullif(count(distinct host_id), 0), 4
        )                                                                 as district_commercial_host_share,
        round(
            count(*) filter (where is_commercial_host) * 1.0 / count(*), 4
        )                                                                 as district_commercial_listings_share

    from basis
    group by 1, 2, 3, 4

),

vorgaenger as (

    -- Die Snapshots liegen unregelmaessig, und mehrere Staende liefern gar keine
    -- Preise (Berlin 2025-12/2026-03, Muenchen 2025-12). Verglichen wird deshalb
    -- mit dem naechsten frueheren Stand, der einen Median hat.
    -- Hinweis: DuckDB erlaubt kein FILTER an Fensterfunktionen, daher der Umweg
    -- ueber den Korrelations-Teilausdruck plus Self-Join.
    select
        k.district_key,
        k.snapshot_date,
        (
            select max(v.snapshot_date)
            from kennzahlen as v
            where v.district_key = k.district_key
              and v.snapshot_date < k.snapshot_date
              and v.district_median_price_eur is not null
        ) as vorgaenger_datum
    from kennzahlen as k

),

verbunden as (

    select
        k.*,
        p.vorgaenger_datum,
        v.district_median_price_eur as vorgaenger_median
    from kennzahlen as k
    left join vorgaenger as p
        on k.district_key = p.district_key
       and k.snapshot_date = p.snapshot_date
    left join kennzahlen as v
        on v.district_key = p.district_key
       and v.snapshot_date = p.vorgaenger_datum

)

select
    row_number() over (order by district_key, snapshot_date) as district_snapshot_id,
    district_key,
    city,
    district,
    snapshot_date,
    district_listing_count,
    district_entire_home_count,
    district_entire_home_share,
    district_listings_with_price,
    district_price_coverage_share,
    district_median_price_eur,
    district_avg_price_eur,
    district_price_outlier_count,
    district_avg_availability_365,
    district_avg_reviews_ltm,
    district_host_count,
    district_commercial_host_count,
    district_commercial_host_share,
    district_commercial_listings_share,

    -- Veraenderung nur ausweisen, wenn der aktuelle Stand selbst einen Median hat.
    -- Staende ohne Preise bleiben leer, nicht 0.
    case
        when district_median_price_eur is not null then vorgaenger_median
    end as district_prev_median_price_eur,
    case
        when district_median_price_eur is not null then vorgaenger_datum
    end as district_prev_snapshot_date,
    case
        when district_median_price_eur is not null
        then round(district_median_price_eur - vorgaenger_median, 2)
    end as district_price_change_eur,
    case
        when district_median_price_eur is not null
        then round((district_median_price_eur - vorgaenger_median) / nullif(vorgaenger_median, 0), 4)
    end as district_price_change_share

from verbunden
