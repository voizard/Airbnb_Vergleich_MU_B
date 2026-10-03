-- Staging: Bezirks-/Stadtteilzuordnung je Stadt.
-- analysis_district ist die einheitliche Analyseebene über beide Städte
-- (Berlin: Bezirk aus neighbourhood_group, München: Stadtbezirk aus neighbourhood).
with quelle as (

    select * from {{ source('inside_airbnb', 'neighbourhoods') }}

)

select
    city,
    district,
    subdistrict,
    coalesce(district, subdistrict) as analysis_district
from quelle
where coalesce(district, subdistrict) is not null
