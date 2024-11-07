# Clickhouse migrations

## 2024-11-15

The minimum supported version of ClickHouse is now `24.11`. The new version of the application uses an experimental JSON column type.

```sql
ALTER TABLE snowplow.local MODIFY COLUMN `session` Tuple(event_index Nullable(UInt64), previous_session_id Nullable(UUID), first_event_id Nullable(UUID), first_event_time Nullable(DateTime64(3, 'UTC')), storage_mechanism LowCardinality(String), unstructured JSON)
ALTER TABLE snowplow.local MODIFY COLUMN `screen` Tuple(type String, view_controller String, top_view_controller String, activity String, fragment String, unstructured JSON)
ALTER TABLE snowplow.local MODIFY COLUMN `page_data` JSON
ALTER TABLE snowplow.local MODIFY COLUMN `user_data` JSON
ALTER TABLE snowplow.local MODIFY COLUMN `geolocation` JSON
ALTER TABLE snowplow.local MODIFY COLUMN `browser` Tuple(family LowCardinality(String), version String, cookie Bool, charset LowCardinality(String), color_depth UInt8, unstructured JSON)
ALTER TABLE snowplow.local MODIFY COLUMN `event` Tuple(action LowCardinality(String), category LowCardinality(String), label String, property JSON, value Float32, unstructured JSON)
```

## 2024-08-30

```sql
ALTER TABLE snowplow.local MODIFY COLUMN `time_extra` Tuple(user DateTime64(3, 'UTC'), sent DateTime64(3, 'UTC'))
ALTER TABLE snowplow.local MODIFY COLUMN `browser` Tuple(family LowCardinality(String), version String, cookie Bool, charset LowCardinality(String), color_depth UInt8, unstructured String)
ALTER TABLE snowplow.local MODIFY COLUMN `device_is` Tuple(mobile Bool, tablet Bool, touch Bool, pc Bool, bot Bool)
ALTER TABLE snowplow.local MODIFY COLUMN `device_extra` Tuple(carrier LowCardinality(String), network_type LowCardinality(String), network_technology LowCardinality(String), open_idfa String, apple_idfa String, apple_idfv String, android_idfa String, battery_level UInt8, battery_state LowCardinality(String), low_power_mode Bool)
```
