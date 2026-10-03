{#
    Einheitlicher Bezirksschluessel fuer alle Modelle.
    Verwendet in dim_neighbourhood, fct_listing_snapshot und den Marts,
    damit Join-Schluessel nirgends doppelt definiert sind.
#}
{% macro bezirksschluessel(city_column, district_column) %}
    {{ city_column }} || '|' || COALESCE({{ district_column }}, 'unbekannt')
{% endmacro %}
