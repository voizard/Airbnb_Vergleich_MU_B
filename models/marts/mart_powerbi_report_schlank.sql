-- Mart: flache Export-Tabelle fuer Power BI (74.898 Zeilen, 32 Spalten).
-- Korn: eine Zeile je Listing und Snapshot, mit Bezirksattributen und dem
-- Fremdschluessel district_snapshot_id (n:1) auf dim_district_snapshot.
-- Die Bezirkskennzahlen selbst liegen in dim_district_snapshot und sind hier
-- bewusst NICHT dupliziert: sie sind nicht additiv und reagieren nicht auf
-- Filter wie den Zimmertyp-Slicer.
-- listing_snapshot_id ist der Primaerschluessel (Zeilenreihenfolge = Exportreihenfolge).
with basis as (

    select
        row_number() over (order by city, snapshot_date, listing_id) as listing_snapshot_id,
        f.*
    from {{ ref('fct_listing_snapshot') }} as f

)

select
    b.listing_snapshot_id,
    ds.district_snapshot_id,
    b.listing_id,
    b.district_key,
    b.city,
    b.snapshot_date,
    year(b.snapshot_date)    as snapshot_year,
    quarter(b.snapshot_date) as snapshot_quarter,
    month(b.snapshot_date)   as snapshot_month,
    b.district,
    b.subdistrict,
    d.subdistrict_count,
    d.centroid_latitude,
    d.centroid_longitude,
    b.room_type,
    b.room_type_de,
    b.room_category,
    b.is_entire_home,
    b.is_commercial_host,
    b.host_id,
    b.host_listings_count,
    b.price_eur,
    b.has_price,
    b.is_price_outlier,
    b.min_nights,
    b.availability_365,
    b.review_count,
    b.reviews_ltm,
    b.reviews_per_month,
    b.last_review_date,
    b.latitude,
    b.longitude
from basis as b
left join {{ ref('dim_district_snapshot') }} as ds
    on b.district_key = ds.district_key
   and b.snapshot_date = ds.snapshot_date
left join {{ ref('dim_neighbourhood') }} as d
    on b.district_key = d.district_key
