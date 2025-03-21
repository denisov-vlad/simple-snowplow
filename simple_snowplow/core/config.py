"""
Configuration management for Simple Snowplow.

Uses Pydantic for type checking while getting values from dynaconf.
"""
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from config import settings as dynaconf_settings
from pydantic_settings import BaseSettings

# Import the dynaconf settings


class SnowplowSchemas(BaseSettings):
    """Schemas configuration for Snowplow."""

    user_data: str = dynaconf_settings.get(
        "common.snowplow.schemas.user_data",
        "dev.snowplow.simple/user_data",
    )
    page_data: str = dynaconf_settings.get(
        "common.snowplow.schemas.page_data",
        "dev.snowplow.simple/page_data",
    )
    screen_data: str = dynaconf_settings.get(
        "common.snowplow.schemas.screen_data",
        "dev.snowplow.simple/screen_data",
    )
    ad_data: str = dynaconf_settings.get(
        "common.snowplow.schemas.ad_data",
        "dev.snowplow.simple/ad_data",
    )
    u2s_data: str = dynaconf_settings.get(
        "common.snowplow.schemas.u2s_data",
        "dev.snowplow.simple/u2s_data",
    )


class SnowplowEndpoints(BaseSettings):
    """Endpoints configuration for Snowplow."""

    post_endpoint: str = dynaconf_settings.get(
        "common.snowplow.endpoints.post_endpoint",
        "/tracker",
    )
    get_endpoint: str = dynaconf_settings.get(
        "common.snowplow.endpoints.get_endpoint",
        "/i",
    )
    proxy_endpoint: str = dynaconf_settings.get(
        "common.snowplow.endpoints.proxy_endpoint",
        "/proxy",
    )
    sendgrid_endpoint: str = dynaconf_settings.get(
        "common.snowplow.endpoints.sendgrid_endpoint",
        "/sendgrid",
    )


class Snowplow(BaseSettings):
    """Snowplow configuration."""

    schemas: SnowplowSchemas = SnowplowSchemas()
    endpoints: SnowplowEndpoints = SnowplowEndpoints()


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    json_format: bool = dynaconf_settings.get("logging.json", False)
    level: str = dynaconf_settings.get("logging.level", "INFO")


class RateLimitingConfig(BaseSettings):
    """Rate limiting configuration."""

    enabled: bool = dynaconf_settings.get("security.rate_limiting.enabled", False)
    max_requests: int = dynaconf_settings.get(
        "security.rate_limiting.max_requests",
        100,
    )
    window_seconds: int = dynaconf_settings.get(
        "security.rate_limiting.window_seconds",
        60,
    )
    ip_whitelist: List[str] = dynaconf_settings.get(
        "security.rate_limiting.ip_whitelist",
        ["127.0.0.1", "::1"],
    )
    path_whitelist: List[str] = dynaconf_settings.get(
        "security.rate_limiting.path_whitelist",
        ["/", "/health"],
    )


class SecurityConfig(BaseSettings):
    """Security configuration."""

    disable_docs: bool = dynaconf_settings.get("security.disable_docs", False)
    trusted_hosts: List[str] = dynaconf_settings.get("security.trusted_hosts", ["*"])
    enable_https_redirect: bool = dynaconf_settings.get(
        "security.https_redirect",
        False,
    )
    rate_limiting: RateLimitingConfig = RateLimitingConfig()


class ElasticAPMConfig(BaseSettings):
    """ElasticAPM configuration."""

    enabled: bool = dynaconf_settings.get("elastic_apm.enabled", False)
    service_name: str = dynaconf_settings.get("common.service_name", "simple-snowplow")
    server_url: Optional[str] = dynaconf_settings.get("elastic_apm.server_url")


class PrometheusConfig(BaseSettings):
    """Prometheus configuration."""

    enabled: bool = dynaconf_settings.get("prometheus.enabled", False)
    metrics_path: str = dynaconf_settings.get("prometheus.metrics_path", "/metrics/")


class ClickHouseConnection(BaseSettings):
    """ClickHouse connection configuration."""

    interface: str = dynaconf_settings.get("clickhouse.connection.interface", "http")
    host: str = dynaconf_settings.get("clickhouse.connection.host", "localhost")
    port: int = dynaconf_settings.get("clickhouse.connection.port", 8123)
    username: str = dynaconf_settings.get("clickhouse.connection.username", "default")
    database: str = dynaconf_settings.get("clickhouse.connection.database", "default")
    password: str = dynaconf_settings.get("clickhouse.connection.password", "")
    connect_timeout: int = dynaconf_settings.get(
        "clickhouse.connection.connect_timeout",
        10,
    )


class ClickHouseConfiguration(BaseSettings):
    """ClickHouse configuration settings."""

    database: str = dynaconf_settings.get(
        "clickhouse.configuration.database",
        "snowplow",
    )
    cluster_name: str = dynaconf_settings.get(
        "clickhouse.configuration.cluster_name",
        "",
    )
    tables: Dict[str, Any] = dynaconf_settings.get(
        "clickhouse.configuration.tables",
        {},
    )


class ClickHouseConfig(BaseSettings):
    """ClickHouse configuration."""

    connection: ClickHouseConnection = ClickHouseConnection()
    configuration: ClickHouseConfiguration = ClickHouseConfiguration()


class CommonConfig(BaseSettings):
    """Common application configuration."""

    demo: bool = dynaconf_settings.get("common.demo", False)
    debug: bool = dynaconf_settings.get("common.debug", False)
    service_name: str = dynaconf_settings.get("common.service_name", "simple-snowplow")
    hostname: str = dynaconf_settings.get("common.hostname", "http://localhost:8000")
    snowplow: Snowplow = Snowplow()


class Settings(BaseSettings):
    """Main application settings populated from dynaconf."""

    logging: LoggingConfig = LoggingConfig()
    security: SecurityConfig = SecurityConfig()
    elastic_apm: ElasticAPMConfig = ElasticAPMConfig()
    prometheus: PrometheusConfig = PrometheusConfig()
    common: CommonConfig = CommonConfig()
    clickhouse: ClickHouseConfig = ClickHouseConfig()

    class Config:
        env_prefix = "SNOWPLOW_"
        case_sensitive = True


settings = Settings()

# Make original dynaconf settings available if needed
dynaconf = dynaconf_settings
