-- Dimension: eine Zeile je Snapshot-Datum (10 Zeilen).
-- Korn: genau ein Datensatz pro snapshot_date, Primaerschluessel snapshot_key.
-- Zweck: eigener Slicer mit EINEM Datentyp. Ohne diese Tabelle haengt der
-- Slicer direkt an fct[snapshot_date]; sobald dort Text und Datum gemischt
-- auftreten, greift der Filter nicht mehr zuverlaessig.
-- snapshot_label fasst Berlin und Muenchen zusammen (beide "Juni 2026"),
-- damit ein Slicer beide Staende zugleich zeigt.
with basis as (

    select distinct
        snapshot_date,
        case month(snapshot_date)
            when 1 then 'Januar'   when 2 then 'Februar' when 3 then 'März'
            when 4 then 'April'    when 5 then 'Mai'     when 6 then 'Juni'
            when 7 then 'Juli'     when 8 then 'August'  when 9 then 'September'
            when 10 then 'Oktober' when 11 then 'November' else 'Dezember'
        end || ' ' || cast(year(snapshot_date) as varchar) as snapshot_label
    from {{ ref('fct_listing_snapshot') }}

)

select
    -- Primaerschluessel: fortlaufend nach Datum, damit die Sortierung stabil ist.
    row_number() over (order by snapshot_date)          as snapshot_key,
    snapshot_date,
    snapshot_label,
    year(snapshot_date)                                 as snapshot_year,
    quarter(snapshot_date)                              as snapshot_quarter,
    month(snapshot_date)                                as snapshot_month,
    -- Sortierschluessel fuer den Slicer: "Juni 2026" chronologisch richtig.
    cast(year(snapshot_date) as varchar) || '-'
        || lpad(cast(month(snapshot_date) as varchar), 2, '0') as snapshot_sort
from basis
order by snapshot_date
