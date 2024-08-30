# Clickhouse migrations

## 2024-08-30

```sql
ALTER TABLE snowplow.local MODIFY COLUMN `time_extra` Tuple(user DateTime64(3, 'UTC'), sent DateTime64(3, 'UTC'))
ALTER TABLE snowplow.local MODIFY COLUMN `browser` Tuple(family LowCardinality(String), version String, cookie Bool, charset LowCardinality(String), color_depth UInt8, unstructured String)
ALTER TABLE snowplow.local MODIFY COLUMN `device_is` Tuple(mobile Bool, tablet Bool, touch Bool, pc Bool, bot Bool)
ALTER TABLE snowplow.local MODIFY COLUMN `device_extra` Tuple(carrier LowCardinality(String), network_type LowCardinality(String), network_technology LowCardinality(String), open_idfa String, apple_idfa String, apple_idfv String, android_idfa String, battery_level UInt8, battery_state LowCardinality(String), low_power_mode Bool)
```
