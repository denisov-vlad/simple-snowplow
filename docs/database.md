Simple-snowplow supports only ClickHouse database.

## First steps

### ClickHouse

If you have multiple shards and set up cluster, use `ON CLUSTER $cluster_name` for all queries below.

* Create database:

```clickhouse
CREATE DATABASE snowplow IF NOT EXISTS
```

* Create MergeTree table:

```clickhouse
CREATE TABLE snowplow.local
(
    `app_id` LowCardinality(String),
    `platform` Enum8('web' = 1, 'mob' = 2, 'pc' = 3, 'srv' = 4, 'app' = 5, 'tv' = 6, 'cnsl' = 7, 'iot' = 8),
    `app_extra` String DEFAULT '',
    `page` String DEFAULT '',
    `referer` Nullable(String) DEFAULT NULL,
    `event_type` Enum8('pv' = 1, 'pp' = 2, 'ue' = 3, 'se' = 4, 'tr' = 5, 'ti' = 6, 's' = 7),
    `event_id` UUID,
    `view_id` String DEFAULT '',
    `session_id` UUID,
    `visit_count` Nullable(UInt32),
    `session_extra` String DEFAULT '',
    `device_id` UUID,
    `device_id_amp` Nullable(String) DEFAULT NULL,
    `user_id` Nullable(String) DEFAULT NULL,
    `time` DateTime64(3, 'UTC'),
    `timezone` Nullable(String) DEFAULT NULL,
    `time_extra` Tuple(`time_user` DateTime64(3, 'UTC'), `time_sent` DateTime64(3, 'UTC')),
    `title` Nullable(String) DEFAULT NULL,
    `screen_extra` String DEFAULT '',
    `page_data` String DEFAULT '',
    `user_data` String DEFAULT '',
    `user_ip` IPv4,
    `user_agent` String DEFAULT '',
    `browser` Tuple(family LowCardinality(String), version Array(String), version_string String, cookie UInt8, charset LowCardinality(String), color_depth UInt8),
    `os` Tuple(family LowCardinality(String), version Array(String), version_string String, language LowCardinality(String)),
    `device` Tuple(family LowCardinality(String), brand LowCardinality(String), model LowCardinality(String)),
    `device_is` Tuple(mobile Int8, tablet Int8, touch Int8, pc Int8, bot Int8),
    `device_extra` String DEFAULT '',
    `resolution` Tuple(browser String, viewport String, page String),
    `event` Tuple(action LowCardinality(String), category LowCardinality(String), label String, property String, value String, unstructured String),
    `extra` String DEFAULT '',
    `tracker` Tuple(version LowCardinality(String), namespace LowCardinality(String))
)
ENGINE = MergeTree()
PARTITION BY (toYYYYMM(time), event_type)
ORDER BY (time, app_id, platform, event_type, device_id, cityHash64(device_id), session_id, view_id, page, event_id)
SAMPLE BY cityHash64(device_id)
SETTINGS index_granularity = 8192;
```

If you have enabled data replication (via `zookeeper` or `clickhouse-keeper`),
use `ReplicatedMergeTree` engine instead of `MergeTree`:
```clickhouse
ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/snowplow', '{replica}')
```

* Create buffer table which allows to send requests directly to ClickHouse without batching:

```clickhouse
CREATE TABLE snowplow.buffer AS snowplow.local ENGINE = Buffer('snowplow', 'local', 16, 10, 100, 10000, 1000000, 10000000, 100000000);
```

*OPTIONAL* For multiple shards use:

```clickhouse
CREATE TABLE snowplow.clickstream ON CLUSTER $cluster_name AS snowplow.local ENGINE = Distributed('$cluster_name', 'snowplow', 'buffer', cityHash64(device_id));
```


Finally:
* if you have 1 shard, use `snowplow.buffer` to insert / select data.
* in other ways use `snowplow.clickstream`.
* **do not use `snowplow.local` to insert data through `simple-snowplow`**
