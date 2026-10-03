{% snapshot listings_history %}

{{
    config(
        target_schema='snapshots',
        unique_key='listing_key',
        strategy='timestamp',
        updated_at='updated_at',
        invalidate_hard_deletes=false
    )
}}

-- SCD Type 2: Preis- und Attributaenderungen je Listing ueber die Snapshots.
-- dbt_valid_from / dbt_valid_to zeigen, ab wann eine Version gueltig war.
select
    city || '|' || cast(listing_id as varchar) as listing_key,
    listing_id,
    city,
    snapshot_date,
    cast(snapshot_date as timestamp)            as updated_at,
    district,
    subdistrict,
    room_type,
    price_eur,
    min_nights,
    availability_365,
    host_id,
    host_listings_count
from {{ ref('stg_airbnb__listings') }}

{% endsnapshot %}
