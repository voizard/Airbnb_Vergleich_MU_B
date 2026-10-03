-- Mart: denormalisierte Export-Tabelle für Power BI.
-- Eine flache Tabelle auf Listing-Ebene mit Bezirksattributen und deutschen
-- Bezeichnungen. In Power BI als Faktentabelle mit den Bezirksattributen
-- nutzbar; district_key ist der Verbindungsschlüssel zu dim_neighbourhood.
select
    f.listing_snapshot_key,
    f.listing_id,
    f.district_key,

    f.city,
    f.snapshot_date,
    year(f.snapshot_date)    as snapshot_year,
    quarter(f.snapshot_date) as snapshot_quarter,
    month(f.snapshot_date)   as snapshot_month,

    f.district,
    f.subdistrict,
    d.subdistrict_count,
    d.centroid_latitude,
    d.centroid_longitude,

    f.room_type,
    f.room_type_de,
    f.room_category,
    f.is_entire_home,
    f.is_commercial_host,

    f.host_id,
    f.host_listings_count,

    f.price_eur,
    f.has_price,
    f.is_price_outlier,
    f.min_nights,
    f.availability_365,
    f.review_count,
    f.reviews_ltm,
    f.reviews_per_month,
    f.last_review_date,
    f.latitude,
    f.longitude
from {{ ref('fct_listing_snapshot') }} as f
left join {{ ref('dim_neighbourhood') }} as d
    on f.district_key = d.district_key
