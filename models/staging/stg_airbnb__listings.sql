-- Staging: Listings aus allen Snapshots, typisiert und benannt.
-- Eine Quelle, ein Modell, keine Aggregation, keine Business-Kennzahlen.
with quelle as (

    select * from {{ source('inside_airbnb', 'listings_all') }}

),

zimmertypen as (

    select * from {{ ref('room_type_mapping') }}

),

umbenannt as (

    select
        listing_id,
        city,
        snapshot_date,
        source_file,

        listing_name,
        host_id,
        host_name,

        district,
        subdistrict,
        -- Analyseebene: Berlin liefert die 12 Bezirke in neighbourhood_group,
        -- München hat dort leere Werte, dort liefert neighbourhood die 25 Stadtbezirke.
        coalesce(district, subdistrict)          as analysis_district,
        case
            when district is not null then 'neighbourhood_group'
            else 'neighbourhood'
        end                                      as analysis_level,
        latitude,
        longitude,

        room_type,
        zimmertypen.room_type_de,
        zimmertypen.room_category,

        price_eur,
        price_eur is not null            as has_price,
        min_nights,
        review_count,
        last_review_date,
        reviews_per_month,
        host_listings_count,
        availability_365,
        reviews_ltm,
        license,

        room_type = 'Entire home/apt'            as is_entire_home,
        coalesce(host_listings_count, 0) > 1     as is_commercial_host

    from quelle
    left join zimmertypen using (room_type)

)

select * from umbenannt
