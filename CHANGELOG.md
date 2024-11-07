# Clickhouse migrations

## 2024-11-15

The minimum supported version of ClickHouse is now `24.11`. The new version of the application uses an experimental JSON column type. Migration of existing tables is not possible. It is recommended to switch to the new table and use the statement below.

```sql
INSERT INTO snowplow.new (app_id, platform, app, page, referer, event_type, event_id, view_id, session_id, visit_count, session, amp, device_id, user_id, time, time_extra, timezone, title, screen, page_data, user_data, user_ip, geolocation, user_agent, browser, os, device, device_is, device_extra, resolution, event, extra, tracker) SELECT
    app_id,
    platform,
    (app.version, app.build),
    page,
    referer,
    event_type,
    event_id,
    view_id,
    session_id,
    visit_count,
    (session.event_index, session.previous_session_id, session.first_event_id, session.first_event_time, session.storage_mechanism, if(isValidJSON(session.unstructured), session.unstructured, '{}')),
    (amp.device_id, amp.client_id, amp.session_id, amp.visit_count, amp.session_engaged, amp.first_event_time, amp.previous_session_time, amp.view_id),
    device_id,
    user_id,
    time_extra.user,
    (time, time_extra.sent),
    timezone,
    title,
    (screen.type, screen.view_controller, screen.top_view_controller, screen.activity, screen.fragment, if(isValidJSON(screen.unstructured), screen.unstructured, '{}')),
    if(isValidJSON(page_data), page_data, '{}'),
    if(isValidJSON(user_data), user_data, '{}'),
    user_ip,
    if(isValidJSON(geolocation), geolocation, '{}'),
    user_agent,
    (browser.family, browser.version, browser.cookie, browser.charset, browser.color_depth, if(isValidJSON(browser.unstructured), browser.unstructured, '{}')),
    (os.family, os.version, os.language),
    (device.brand, device.model),
    (device_is.mobile, device_is.tablet, device_is.touch, device_is.pc, device_is.bot),
    (device_extra.carrier, device_extra.network_type, device_extra.network_technology, device_extra.open_idfa, device_extra.apple_idfa, device_extra.apple_idfv, device_extra.android_idfa, device_extra.battery_level, device_extra.battery_state, device_extra.low_power_mode),
    (resolution.browser, resolution.viewport, resolution.page),
    (event.action, event.category, event.label, if(isValidJSON(event.property), event.property, '{}'), event.value, if(isValidJSON(event.unstructured), event.unstructured, '{}')),
    if(isValidJSON(extra), extra, '{}'),
    (tracker.version, tracker.namespace)
FROM snowplow.old
```

## 2024-08-30

```sql
ALTER TABLE snowplow.local MODIFY COLUMN `time_extra` Tuple(user DateTime64(3, 'UTC'), sent DateTime64(3, 'UTC'))
ALTER TABLE snowplow.local MODIFY COLUMN `browser` Tuple(family LowCardinality(String), version String, cookie Bool, charset LowCardinality(String), color_depth UInt8, unstructured String)
ALTER TABLE snowplow.local MODIFY COLUMN `device_is` Tuple(mobile Bool, tablet Bool, touch Bool, pc Bool, bot Bool)
ALTER TABLE snowplow.local MODIFY COLUMN `device_extra` Tuple(carrier LowCardinality(String), network_type LowCardinality(String), network_technology LowCardinality(String), open_idfa String, apple_idfa String, apple_idfv String, android_idfa String, battery_level UInt8, battery_state LowCardinality(String), low_power_mode Bool)
```
