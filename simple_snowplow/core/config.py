import os
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class SnowplowSchemas(BaseModel):
    user_data: str = "dev.snowplow.simple/user_data"
    page_data: str = "dev.snowplow.simple/page_data"
    screen_data: str = "dev.snowplow.simple/screen_data"
    ad_data: str = "dev.snowplow.simple/ad_data"
    u2s_data: str = "dev.snowplow.simple/u2s_data"


class SnowplowEndpoints(BaseModel):
    post_endpoint: str = "/tracker"
    get_endpoint: str = "/i"
    proxy_endpoint: str = "/proxy"
    sendgrid_endpoint: str = "/sendgrid"


class Snowplow(BaseModel):
    schemas: SnowplowSchemas = SnowplowSchemas()
    endpoints: SnowplowEndpoints = SnowplowEndpoints()


class LoggingConfig(BaseModel):
    json_format: bool = False
    level: str = "WARNING"


class RateLimitingConfig(BaseModel):
    enabled: bool = False
    max_requests: int = 100
    window_seconds: int = 60
    ip_whitelist: list[str] = []
    path_whitelist: list[str] = ["/health"]


class SecurityConfig(BaseModel):
    disable_docs: bool = False
    trusted_hosts: list[str] = ["*"]
    enable_https_redirect: bool = False
    trust_proxy_headers: bool = True
    rate_limiting: RateLimitingConfig = RateLimitingConfig()


class ElasticAPMConfig(BaseModel):
    enabled: bool = False
    service_name: str = "simple-snowplow"
    server_url: str | None = None


class PrometheusConfig(BaseModel):
    enabled: bool = False
    metrics_path: str = "/metrics/"


class SentryConfig(BaseModel):
    enabled: bool = False
    dsn: str | None = None
    traces_sample_rate: float = 0.0
    environment: str = (
        "prod" if os.getenv("SNOWPLOW_ENV", "development") == "production" else "dev"
    )


class ProxyConfig(BaseModel):
    domains: list[str] = ["google-analytics.com", "www.googletagmanager.com"]
    paths: list[str] = ["analytics.js", "gtm.js"]


class PerformanceConfig(BaseModel):
    max_concurrent_connections: int = 100
    db_pool_size: int = 5
    db_pool_overflow: int = 10


class ClickHouseConnection(BaseModel):
    interface: str = "http"
    host: str = "clickhouse"
    port: int = 8123
    username: str = "default"
    database: str = "default"
    password: str = "password"
    connect_timeout: int = 10


class ClickHouseConfiguration(BaseModel):
    database: str = "snowplow"
    cluster_name: str = ""

    # Can be overridden via environment variables such as:
    # SNOWPLOW_CLICKHOUSE__CONFIGURATION__TABLES__SNOWPLOW__LOCAL__ENGINE=
    #   "ReplacingMergeTree()"
    tables: dict[str, Any] = {
        "snowplow": {
            "enabled": True,
            "local": {
                "name": "local",
                "engine": "MergeTree()",
                "partition_by": "toYYYYMM(time)",
                "order_by": ", ".join([
                    "app",
                    "platform",
                    "app_id",
                    "event_type",
                    "toDate(time)",
                    "event.category",
                    "event.action",
                    "page",
                    "device_id",
                    "cityHash64(device_id)",
                    "session_id",
                    "time",
                ]),
                "sample_by": "cityHash64(device_id)",
                "settings": "index_granularity = 8192",
            },
            "distributed": {
                "name": "distributed",
                "sample_by": "cityHash64(device_id)",
            },
        },
    }


class ClickHouseConfig(BaseModel):
    connection: ClickHouseConnection = ClickHouseConnection()
    configuration: ClickHouseConfiguration = ClickHouseConfiguration()
    tables: dict[str, Any] = {}


class CommonConfig(BaseModel):
    demo: bool = False
    debug: bool = False
    service_name: str = "simple-snowplow"
    hostname: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    snowplow: Snowplow = Snowplow()


class Settings(BaseSettings):
    """Main application settings populated from file + env vars.

    Nested models are supported via double underscore environment variable keys
    (e.g. ``SNOWPLOW_LOGGING__LEVEL=DEBUG``).
    """

    model_config = SettingsConfigDict(
        env_prefix="SNOWPLOW_",
        case_sensitive=False,
        env_nested_delimiter="__",
    )
    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    elastic_apm: ElasticAPMConfig = ElasticAPMConfig()
    prometheus: PrometheusConfig = PrometheusConfig()
    sentry: SentryConfig = SentryConfig()
    proxy: ProxyConfig = ProxyConfig()
    performance: PerformanceConfig = PerformanceConfig()
    common: CommonConfig = CommonConfig()
    clickhouse: ClickHouseConfig = ClickHouseConfig()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Eagerly instantiate for backwards compatibility with previous import style
settings = get_settings()
