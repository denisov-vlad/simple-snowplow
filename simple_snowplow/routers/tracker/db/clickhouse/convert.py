from enum import Enum

from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import DateTime64
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Enum8
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import IPv4
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import JSON
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import LowCardinality
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Nullable
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import String
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Tuple
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UInt64
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UUID
from clickhouse_connect.datatypes.base import TypeDef


class Platform(Enum):
    web = 1
    mob = 2
    pc = 3
    srv = 4
    app = 5
    tv = 6
    cnsl = 7
    iot = 8


class EventType(Enum):
    pv = 1
    pp = 2
    ue = 3
    se = 4
    tr = 5
    ti = 6
    s = 7


table_fields = [
    {
        "column_name": "app_id",
        "payload_name": "aid",
        "type": LowCardinality(String),
    },
    {
        "column_name": "platform",
        "payload_name": "p",
        "type": Enum8(enum=Platform),
    },
    {
        "column_name": "app",
        "payload_name": ("app_version", "app_build"),
        "type": Tuple(
            type_def=TypeDef(keys=("version", "build"), values=("String", "String")),
        ),
    },
    {
        "column_name": "page",
        "payload_name": "url",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "referer",
        "payload_name": "refr",
        "type": Nullable(String),
        "default_type": "DEFAULT",
        "default_expression": "NULL",
    },
    {
        "column_name": "event_type",
        "payload_name": "e",
        "type": Enum8(enum=EventType),
    },
    {"column_name": "event_id", "payload_name": "eid", "type": UUID()},
    {"column_name": "view_id", "payload_name": "view_id", "type": UUID()},
    {"column_name": "session_id", "payload_name": "sid", "type": UUID()},
    {
        "column_name": "visit_count",
        "payload_name": "vid",
        "type": Nullable(UInt64),
    },
    {
        "column_name": "session",
        "payload_name": (
            "event_index",
            "previous_session_id",
            "first_event_id",
            "first_event_time",
            "storage_mechanism",
            "session_unstructured",
        ),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "event_index",
                    "previous_session_id",
                    "first_event_id",
                    "first_event_time",
                    "storage_mechanism",
                    "unstructured",
                ),
                values=(
                    "Nullable(UInt64)",
                    "Nullable(UUID)",
                    "Nullable(UUID)",
                    "Nullable(DateTime64(3, 'UTC'))",
                    "LowCardinality(String)",
                    "JSON",
                ),
            ),
        ),
    },
    {
        "column_name": "amp",
        "payload_name": (
            "amp_device_id",
            "amp_client_id",
            "amp_session_id",
            "amp_visit_count",
            "amp_session_engaged",
            "amp_first_event_time",
            "amp_previous_session_time",
            "amp_view_id",
        ),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "device_id",
                    "client_id",
                    "session_id",
                    "visit_count",
                    "session_engaged",
                    "first_event_time",
                    "previous_session_time",
                    "view_id",
                ),
                values=(
                    "String",
                    "String",
                    "UInt64",
                    "UInt64",
                    "UInt8",
                    "Nullable(DateTime64(3, 'UTC'))",
                    "Nullable(DateTime64(3, 'UTC'))",
                    "String",
                ),
            ),
        ),
    },
    {"column_name": "device_id", "payload_name": "duid", "type": UUID()},
    {
        "column_name": "user_id",
        "payload_name": "uid",
        "type": Nullable(String),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "time",
        "payload_name": "rtm",
        "type": DateTime64(3, "UTC"),
    },
    {
        "column_name": "time_extra",
        "payload_name": ("dtm", "stm"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("user", "sent"),
                values=("DateTime64(3, 'UTC')", "DateTime64(3, 'UTC')"),
            ),
        ),
    },
    {
        "column_name": "timezone",
        "payload_name": "tz",
        "type": Nullable(String),
        "default_type": "DEFAULT",
        "default_expression": "NULL",
    },
    {
        "column_name": "title",
        "payload_name": "page",
        "type": Nullable(String),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "screen",
        "payload_name": (
            "screen_type",
            "screen_vc",
            "screen_tvc",
            "screen_activity",
            "screen_fragment",
            "screen_unstructured",
        ),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "type",
                    "view_controller",
                    "top_view_controller",
                    "activity",
                    "fragment",
                    "unstructured",
                ),
                values=(
                    "String",
                    "String",
                    "String",
                    "String",
                    "String",
                    "JSON",
                ),
            ),
        ),
    },
    {"column_name": "page_data", "payload_name": "page_data", "type": JSON()},
    {"column_name": "user_data", "payload_name": "user_data", "type": JSON()},
    {"column_name": "user_ip", "payload_name": "user_ip", "type": IPv4()},
    {
        "column_name": "geolocation",
        "payload_name": "geolocation",
        "type": JSON(),
    },
    {
        "column_name": "user_agent",
        "payload_name": "user_agent",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "browser",
        "payload_name": (
            "browser_family",
            "browser_version_string",
            "cookie",
            "cs",
            "cd",
            "browser_unstructured",
        ),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "family",
                    "version",
                    "cookie",
                    "charset",
                    "color_depth",
                    "unstructured",
                ),
                values=(
                    "LowCardinality(String)",
                    "String",
                    "Bool",
                    "LowCardinality(String)",
                    "UInt8",
                    "JSON",
                ),
            ),
        ),
    },
    {
        "column_name": "os",
        "payload_name": ("os_family", "os_version_string", "lang"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("family", "version", "language"),
                values=("LowCardinality(String)", "String", "LowCardinality(String)"),
            ),
        ),
    },
    {
        "column_name": "device",
        "payload_name": ("device_brand", "device_model"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("brand", "model"),
                values=("LowCardinality(String)", "LowCardinality(String)"),
            ),
        ),
    },
    {
        "column_name": "device_is",
        "payload_name": "device_is",
        "type": Tuple(
            type_def=TypeDef(
                keys=("mobile", "tablet", "touch", "pc", "bot"),
                values=("Bool", "Bool", "Bool", "Bool", "Bool"),
            ),
        ),
    },
    {
        "column_name": "device_extra",
        "payload_name": (
            "carrier",
            "network_type",
            "network_technology",
            "open_idfa",
            "apple_idfa",
            "apple_idfv",
            "android_idfa",
            "battery_level",
            "battery_state",
            "low_power_mode",
        ),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "carrier",
                    "network_type",
                    "network_technology",
                    "open_idfa",
                    "apple_idfa",
                    "apple_idfv",
                    "android_idfa",
                    "battery_level",
                    "battery_state",
                    "low_power_mode",
                ),
                values=(
                    "LowCardinality(String)",
                    "LowCardinality(String)",
                    "LowCardinality(String)",
                    "String",
                    "String",
                    "String",
                    "String",
                    "UInt8",
                    "LowCardinality(String)",
                    "Bool",
                ),
            ),
        ),
    },
    {
        "column_name": "resolution",
        "payload_name": ("res", "vp", "ds"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("browser", "viewport", "page"),
                values=("String", "String", "String"),
            ),
        ),
    },
    {
        "column_name": "event",
        "payload_name": ("se_ac", "se_ca", "se_la", "se_pr", "se_va", "ue"),
        "type": Tuple(
            type_def=TypeDef(
                keys=(
                    "action",
                    "category",
                    "label",
                    "property",
                    "value",
                    "unstructured",
                ),
                values=(
                    "LowCardinality(String)",
                    "LowCardinality(String)",
                    "String",
                    "JSON",
                    "Float32",
                    "JSON",
                ),
            ),
        ),
    },
    {"column_name": "extra", "payload_name": "extra", "type": JSON()},
    {
        "column_name": "tracker",
        "payload_name": ("tv", "tna"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("version", "namespace"),
                values=("LowCardinality(String)", "LowCardinality(String)"),
            ),
        ),
    },
]
