-- Singular Test: Ein Listing darf je Stadt und Snapshot nur einmal vorkommen.
-- Ersetzt den dbt_utils-Test unique_combination_of_columns, weil das Projekt
-- bewusst ohne externe Pakete laeuft.
select
    city,
    snapshot_date,
    listing_id,
    count(*) as anzahl
from {{ ref('stg_airbnb__listings') }}
group by 1, 2, 3
having count(*) > 1
