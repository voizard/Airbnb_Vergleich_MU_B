-- Mart: Kennzahlen je Bezirk und Snapshot.
-- Korn: eine Zeile je Stadt, Bezirk und Snapshot-Datum.
-- Preisgrenzen: Ausreisser oberhalb von var('max_plausibler_preis_eur') werden
-- aus den Preiskennzahlen ausgeschlossen, aber gezaehlt (price_outlier_count).
with basis as (

    select * from {{ ref('fct_listing_snapshot') }}

),

kennzahlen as (

    select
        district_key,
        city,
        district,
        snapshot_date,

        count(*)                                                        as listing_count,
        count(*) filter (where is_entire_home)                          as entire_home_count,
        round(count(*) filter (where is_entire_home) * 1.0 / count(*), 4) as entire_home_share,

        count(*) filter (where has_price)                               as listings_with_price,
        round(count(*) filter (where has_price) * 1.0 / count(*), 4)     as price_coverage_share,
        round(
            median(price_eur) filter (where has_price and not is_price_outlier), 2
        )                                                               as median_price_eur,
        round(
            avg(price_eur) filter (where has_price and not is_price_outlier), 2
        )                                                               as avg_price_eur,
        count(*) filter (where is_price_outlier)                        as price_outlier_count,

        round(avg(availability_365), 1)                                 as avg_availability_365,
        round(avg(reviews_ltm), 1)                                      as avg_reviews_ltm,

        count(distinct host_id)                                         as host_count,
        count(distinct host_id) filter (where is_commercial_host)       as commercial_host_count,
        round(
            count(distinct host_id) filter (where is_commercial_host) * 1.0
            / nullif(count(distinct host_id), 0), 4
        )                                                               as commercial_host_share,
        round(
            count(*) filter (where is_commercial_host) * 1.0 / count(*), 4
        )                                                               as listings_from_commercial_hosts_share

    from basis
    group by 1, 2, 3, 4

)

select * from kennzahlen
