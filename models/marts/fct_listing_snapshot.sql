{{
    config(
        materialized='incremental',
        unique_key='listing_snapshot_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

-- Faktentabelle auf Listing-Ebene. Korn: eine Zeile je Listing und Snapshot.
-- Inkrementell: es werden nur Snapshots verarbeitet, die noch nicht in der
-- Zieltabelle stehen. unique_key verhindert Doppelzeilen bei erneutem Lauf.
with listings as (

    select * from {{ ref('stg_airbnb__listings') }}
    {% if is_incremental() %}
    where snapshot_date > (select max(snapshot_date) from {{ this }})
    {% endif %}

)

select
    city || '|' || cast(snapshot_date as varchar) || '|' || cast(listing_id as varchar)
                                             as listing_snapshot_key,
    {{ bezirksschluessel('city', 'analysis_district') }} as district_key,

    listing_id,
    city,
    snapshot_date,
    analysis_district                        as district,
    subdistrict,
    analysis_level,

    room_type,
    room_type_de,
    room_category,
    is_entire_home,
    is_commercial_host,
    host_id,
    host_listings_count,

    price_eur,
    has_price,
    price_eur > {{ var('max_plausibler_preis_eur') }} as is_price_outlier,
    min_nights,
    availability_365,
    review_count,
    reviews_ltm,
    reviews_per_month,
    last_review_date,
    latitude,
    longitude
from listings
