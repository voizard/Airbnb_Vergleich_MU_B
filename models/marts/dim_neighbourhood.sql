-- Dimension: Bezirke je Stadt mit Näherungskoordinaten aus den Listings.
-- Korn: eine Zeile je Stadt und Analysebezirk.
with bezirke as (

    select
        city,
        analysis_district,
        count(distinct subdistrict) as subdistrict_count
    from {{ ref('stg_airbnb__neighbourhoods') }}
    group by 1, 2

),

geo as (

    select
        city,
        analysis_district,
        avg(latitude)  as centroid_latitude,
        avg(longitude) as centroid_longitude
    from {{ ref('stg_airbnb__listings') }}
    group by 1, 2

)

select
    {{ bezirksschluessel('bezirke.city', 'bezirke.analysis_district') }} as district_key,
    bezirke.city,
    bezirke.analysis_district               as district,
    bezirke.subdistrict_count,
    round(geo.centroid_latitude, 6)         as centroid_latitude,
    round(geo.centroid_longitude, 6)        as centroid_longitude
from bezirke
left join geo
    on bezirke.city = geo.city
   and bezirke.analysis_district = geo.analysis_district
