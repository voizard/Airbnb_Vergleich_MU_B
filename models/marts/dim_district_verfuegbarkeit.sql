-- Dimension: Verfuegbarkeit je Bezirk und Snapshot (148 Zeilen).
-- Korn: eine Zeile je Stadt, Bezirk und Snapshot-Datum - identisch zu
-- dim_district_snapshot, gleicher Primaerschluessel district_snapshot_id.
--
-- Warum eine eigene Tabelle: In Power BI ist die Spaltenzahl der Quellabfrage
-- festgeschrieben (Csv.Document ... Columns=n). Zusaetzliche Spalten in einer
-- bestehenden Datei fallen dadurch still heraus. Diese Tabelle ist erweiterbar,
-- ohne die bestehenden Importe anzufassen - und sie ist absichtlich
-- selbsttragend: Verfuegbarkeit UND Preis, damit der Scatter aus dieser einen
-- Tabelle gebaut werden kann.
--
-- Alle Kennzahlen sind Anteile bzw. Mittel/Median auf Bezirksebene und NICHT
-- additiv: nie summieren, im Visual Mittelwert oder Max verwenden. Fuer
-- stadtweite Anteile die Bezirke mit verf_basis_inserate gewichten.
with basis as (

    select * from {{ ref('fct_listing_snapshot') }}

),

kennzahlen as (

    select
        district_key,
        city,
        district,
        snapshot_date,

        count(*)                                                             as verf_basis_inserate,
        count(*) filter (where availability_365 > 0)                         as verf_aktive_inserate,
        round(avg(availability_365), 1)                                      as verf_mittel_alle,
        round(median(availability_365), 1)                                   as verf_median_alle,
        round(avg(availability_365) filter (where availability_365 > 0), 1)  as verf_mittel_aktiv,

        -- Vier Eimer statt einer Zahl: die Verteilung ist dreigipflig (viele
        -- gesperrte Kalender, viele ab 300 Tagen), das Mittel verschweigt das.
        -- Die vier Anteile summieren sich auf 1.
        round(count(*) filter (where availability_365 = 0) * 1.0 / count(*), 4)                 as verf_anteil_gesperrt,
        round(count(*) filter (where availability_365 between 1 and 89) * 1.0 / count(*), 4)    as verf_anteil_1_89,
        round(count(*) filter (where availability_365 between 90 and 299) * 1.0 / count(*), 4)  as verf_anteil_90_299,
        round(count(*) filter (where availability_365 >= 300) * 1.0 / count(*), 4)              as verf_anteil_300plus,

        -- Preis je Bezirk, gleiche Definition wie in dim_district_snapshot
        -- (Ausreisser > var('max_plausibler_preis_eur') ausgeschlossen). Liegt
        -- hier mit drin, damit der Scatter Verfuegbarkeit x Preis ohne
        -- Beziehung und ohne die alte Dim gebaut werden kann.
        count(*) filter (where has_price)                                     as inserate_mit_preis,
        round(count(*) filter (where has_price) * 1.0 / count(*), 4)          as preis_abdeckung_share,
        round(median(price_eur) filter (where has_price and not is_price_outlier), 2) as median_preis_eur,
        round(avg(price_eur) filter (where has_price and not is_price_outlier), 2)    as mittel_preis_eur

    from basis
    group by 1, 2, 3, 4

)

select
    d.district_snapshot_id,
    k.district_key,
    k.city,
    k.district,
    k.snapshot_date,
    d.snapshot_label,
    k.verf_basis_inserate,
    k.verf_aktive_inserate,
    k.verf_mittel_alle,
    k.verf_median_alle,
    k.verf_mittel_aktiv,
    k.verf_anteil_gesperrt,
    k.verf_anteil_1_89,
    k.verf_anteil_90_299,
    k.verf_anteil_300plus,
    k.inserate_mit_preis,
    k.preis_abdeckung_share,
    k.median_preis_eur,
    k.mittel_preis_eur
from kennzahlen as k
inner join {{ ref('dim_district_snapshot') }} as d
    on k.district_key = d.district_key
   and k.snapshot_date = d.snapshot_date
