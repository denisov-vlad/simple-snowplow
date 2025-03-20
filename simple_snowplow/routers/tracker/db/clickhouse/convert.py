from enum import Enum

from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Array
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import DateTime
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import DateTime64
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Enum8
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import IPv4
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import LowCardinality
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Nullable
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import String
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import Tuple
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UInt16
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UInt32
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UInt64
from clickhouse_connect.cc_sqlalchemy.datatypes.sqltypes import UUID
from clickhouse_connect.datatypes.base import TypeDef
from clickhouse_connect.datatypes.dynamic import JSON


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


snowplow_fields = [
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
        "column_name": "app_info",
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
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
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
        "payload_name": "amp",
        "type": JSON(type_def=TypeDef()),
        "default_expression": {},
    },
    {"column_name": "device_id", "payload_name": "duid", "type": UUID()},
    {
        "column_name": "user_id",
        "payload_name": "uid",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "time",
        "payload_name": "dtm",
        "type": DateTime64(3, "UTC"),
    },
    {
        "column_name": "time_extra",
        "payload_name": ("rtm", "stm"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("received", "sent"),
                values=("DateTime64(3, 'UTC')", "DateTime64(3, 'UTC')"),
            ),
        ),
    },
    {
        "column_name": "timezone",
        "payload_name": "tz",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "title",
        "payload_name": "page",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "screen",
        "payload_name": "screen",
        "type": JSON(type_def=TypeDef()),
    },
    {
        "column_name": "page_data",
        "payload_name": "page_data",
        "type": JSON(type_def=TypeDef()),
    },
    {
        "column_name": "user_data",
        "payload_name": "user_data",
        "type": JSON(type_def=TypeDef()),
        "default_expression": {},
    },
    {"column_name": "user_ip", "payload_name": "user_ip", "type": IPv4()},
    {
        "column_name": "geolocation",
        "payload_name": "geolocation",
        "type": JSON(type_def=TypeDef()),
        "default_expression": {},
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
        "payload_name": ("browser_family", "browser_version_string", "browser_extra"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("family", "version", "extra"),
                values=("LowCardinality(String)", "String", "JSON"),
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
        "payload_name": ("device_brand", "device_model", "device_extra"),
        "type": Tuple(
            type_def=TypeDef(
                keys=("brand", "model", "extra"),
                values=("LowCardinality(String)", "LowCardinality(String)", "JSON"),
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
        "column_name": "resolution",
        "payload_name": ("res", "vp", "ds"),
        "type": Tuple(
            type_def=TypeDef(
                # LC?
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
    {
        "column_name": "extra",
        "payload_name": "extra",
        "type": JSON(type_def=TypeDef()),
        "default_expression": {},
    },
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
    {
        "column_name": "app",
        "payload_name": None,
        "type": LowCardinality(String),
        "default_type": "MATERIALIZED",
        "default_expression": "if(platform = 'mob', tracker.2, app_id)",
    },
]


sendgrid_fields = [
    {
        "column_name": "email",
        "payload_name": "email",
        "type": String(),
    },
    {
        "column_name": "time",
        "payload_name": "timestamp",
        "type": DateTime("UTC"),
    },
    {
        "column_name": "smtp_id",
        "payload_name": "smtp_id",
        "type": String(),
    },
    {
        "column_name": "event",
        "payload_name": "event",
        "type": LowCardinality(String),
    },
    {
        "column_name": "category",
        "payload_name": "category",
        "type": Array(String),
    },
    {
        "column_name": "sg_event_id",
        "payload_name": "sg_event_id",
        "type": String(),
    },
    {
        "column_name": "sg_message_id",
        "payload_name": "sg_message_id",
        "type": String(),
    },
    {
        "column_name": "response",
        "payload_name": "response",
        "type": LowCardinality(String),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "attempt",
        "payload_name": "attempt",
        "type": UInt16(),
        "default_type": "DEFAULT",
        "default_expression": 0,
    },
    {
        "column_name": "user_agent",
        "payload_name": "useragent",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "ip",
        "payload_name": "ip",
        "type": IPv4(),
    },
    {
        "column_name": "url",
        "payload_name": "url",
        "type": String(),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "reason",
        "payload_name": "reason",
        "type": LowCardinality(String),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "status",
        "payload_name": "status",
        "type": LowCardinality(String),
        "default_type": "DEFAULT",
        "default_expression": "''",
    },
    {
        "column_name": "asm_group_id",
        "payload_name": "asm_group_id",
        "type": UInt32(),
        "default_type": "DEFAULT",
        "default_expression": 0,
    },
]


fields = {"snowplow": snowplow_fields, "sendgrid": sendgrid_fields}
