"""
Configuration management for Simple Snowplow.

This module defines all configuration models using Pydantic for validation.
Settings can be configured via environment variables with the SNOWPLOW_ prefix.
"""

import os
from functools import lru_cache
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .constants import (
    APP_SLUG,
    DEFAULT_CLICKHOUSE_DATABASE,
    DEFAULT_CLICKHOUSE_HOST,
    DEFAULT_CLICKHOUSE_INTERFACE,
    DEFAULT_CLICKHOUSE_PORT,
    DEFAULT_CLICKHOUSE_USERNAME,
    DEFAULT_DATABASE_NAME,
    DEFAULT_DB_CONNECT_TIMEOUT,
    DEFAULT_GET_ENDPOINT,
    DEFAULT_INGEST_MODE,
    DEFAULT_METRICS_PATH,
    DEFAULT_POST_ENDPOINT,
    DEFAULT_PROXY_ENDPOINT,
    DEFAULT_RABBITMQ_BATCH_SIZE,
    DEFAULT_RABBITMQ_BATCH_TIMEOUT_MS,
    DEFAULT_RABBITMQ_HOST,
    DEFAULT_RABBITMQ_PORT,
    DEFAULT_RABBITMQ_PREFETCH_COUNT,
    DEFAULT_RABBITMQ_QUEUE_NAME,
    DEFAULT_RABBITMQ_RETRY_DELAY_MS,
    DEFAULT_SENDGRID_ENDPOINT,
    ENV_DEVELOPMENT,
    ENV_PRODUCTION,
    LOG_LEVEL_WARNING,
    SENTRY_ENV_DEV,
    SENTRY_ENV_PROD,
)


class SnowplowSchemas(BaseModel):
    """Schema identifiers for Snowplow events."""

    user_data: str = "dev.snowplow.simple/user_data"
    page_data: str = "dev.snowplow.simple/page_data"
    screen_data: str = "dev.snowplow.simple/screen_data"
    ad_data: str = "dev.snowplow.simple/ad_data"
    u2s_data: str = "dev.snowplow.simple/u2s_data"


class SnowplowEndpoints(BaseModel):
    """Endpoint paths for Snowplow collectors."""

    post_endpoint: str = DEFAULT_POST_ENDPOINT
    get_endpoint: str = DEFAULT_GET_ENDPOINT
    proxy_endpoint: str = DEFAULT_PROXY_ENDPOINT
    sendgrid_endpoint: str = DEFAULT_SENDGRID_ENDPOINT


class Snowplow(BaseModel):
    """Snowplow-specific configuration."""

    schemas: SnowplowSchemas = SnowplowSchemas()
    endpoints: SnowplowEndpoints = SnowplowEndpoints()
    user_ip_header: str = "X-Forwarded-For"

    @field_validator("user_ip_header")
    @classmethod
    def validate_user_ip_header(cls, value: str) -> str:
        """Ensure the user IP header name is not empty."""
        header_name = value.strip()
        if not header_name:
            raise ValueError("user_ip_header must not be empty")
        return header_name


class LoggingConfig(BaseModel):
    """Logging configuration."""

    json_format: bool = False
    level: str = LOG_LEVEL_WARNING

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Ensure log level is uppercase and valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper_v


class SecurityConfig(BaseModel):
    """Security-related configuration."""

    disable_docs: bool = False
    trusted_hosts: list[str] = ["*"]
    enable_https_redirect: bool = False
    trust_proxy_headers: bool = True


class ElasticAPMConfig(BaseModel):
    """Elastic APM configuration."""

    enabled: bool = False
    service_name: str = APP_SLUG
    server_url: str | None = None


class PrometheusConfig(BaseModel):
    """Prometheus metrics configuration."""

    enabled: bool = False
    metrics_path: str = DEFAULT_METRICS_PATH


class SentryConfig(BaseModel):
    """Sentry error tracking configuration."""

    enabled: bool = False
    dsn: str | None = None
    traces_sample_rate: float = 0.0
    environment: str = (
        SENTRY_ENV_PROD
        if os.getenv("SNOWPLOW_ENV", ENV_DEVELOPMENT) == ENV_PRODUCTION
        else SENTRY_ENV_DEV
    )

    @field_validator("traces_sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: float) -> float:
        """Ensure sample rate is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("traces_sample_rate must be between 0.0 and 1.0")
        return v


class ProxyConfig(BaseModel):
    """Proxy configuration for external services."""

    domains: list[str] = ["google-analytics.com", "www.googletagmanager.com"]
    paths: list[str] = ["analytics.js", "gtm.js"]


class PerformanceConfig(BaseModel):
    """Performance tuning configuration."""

    max_concurrent_connections: int = 100
    db_pool_size: int = 5
    db_pool_overflow: int = 10

    @field_validator("db_pool_size", "db_pool_overflow", "max_concurrent_connections")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        """Ensure values are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v


class ClickHouseConnection(BaseModel):
    """ClickHouse connection parameters."""

    interface: str = DEFAULT_CLICKHOUSE_INTERFACE
    host: str = DEFAULT_CLICKHOUSE_HOST
    port: int = DEFAULT_CLICKHOUSE_PORT
    username: str = DEFAULT_CLICKHOUSE_USERNAME
    database: str = DEFAULT_CLICKHOUSE_DATABASE
    password: str = "password"
    connect_timeout: int = DEFAULT_DB_CONNECT_TIMEOUT


class ClickHouseConfiguration(BaseModel):
    """ClickHouse table configuration."""

    database: str = DEFAULT_DATABASE_NAME
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
    """Complete ClickHouse configuration."""

    connection: ClickHouseConnection = ClickHouseConnection()
    configuration: ClickHouseConfiguration = ClickHouseConfiguration()
    tables: dict[str, Any] = {}


class DirectInsertConfig(BaseModel):
    """Direct ClickHouse insert settings."""

    async_insert: bool = True
    wait_for_async_insert: bool = True


class RabbitMQConfig(BaseModel):
    """RabbitMQ-backed ingest settings."""

    host: str = DEFAULT_RABBITMQ_HOST
    port: int = DEFAULT_RABBITMQ_PORT
    username: str = "guest"
    password: str = "guest"
    virtualhost: str = "/"
    queue_name: str = DEFAULT_RABBITMQ_QUEUE_NAME
    prefetch_count: int = DEFAULT_RABBITMQ_PREFETCH_COUNT
    batch_size: int = DEFAULT_RABBITMQ_BATCH_SIZE
    batch_timeout_ms: int = DEFAULT_RABBITMQ_BATCH_TIMEOUT_MS
    retry_delay_ms: int = DEFAULT_RABBITMQ_RETRY_DELAY_MS

    @field_validator(
        "port",
        "prefetch_count",
        "batch_size",
        "batch_timeout_ms",
        "retry_delay_ms",
    )
    @classmethod
    def validate_positive(cls, value: int) -> int:
        """Ensure queue settings are positive integers."""
        if value <= 0:
            raise ValueError("Value must be positive")
        return value


class IngestConfig(BaseModel):
    """Ingest pipeline settings."""

    mode: Literal["direct", "rabbitmq"] = DEFAULT_INGEST_MODE
    direct: DirectInsertConfig = DirectInsertConfig()
    rabbitmq: RabbitMQConfig = RabbitMQConfig()


class CommonConfig(BaseModel):
    """Common application configuration."""

    demo: bool = False
    debug: bool = False
    service_name: str = APP_SLUG
    hostname: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    snowplow: Snowplow = Snowplow()


class Settings(BaseSettings):
    """Main application settings populated from file + env vars.

    Nested models are supported via double underscore environment variable keys
    (e.g. ``SNOWPLOW_LOGGING__LEVEL=DEBUG``).

    Example:
        >>> settings = get_settings()
        >>> settings.logging.level
        'WARNING'
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
    ingest: IngestConfig = IngestConfig()

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return os.getenv("SNOWPLOW_ENV", ENV_DEVELOPMENT) == ENV_PRODUCTION

    @property
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.common.debug


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get the application settings (cached)."""
    return Settings()


# Eagerly instantiate for backwards compatibility with previous import style
settings = get_settings()
