"""
Configuration management for Simple Snowplow.

Uses Pydantic for type checking while getting values from dynaconf.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

from dynaconf import Dynaconf
from pydantic_settings import BaseSettings

# Base configuration path
CONFIG_DIR = Path(__file__).parent.parent
SETTINGS_PATH = CONFIG_DIR / "settings.toml"
SECRETS_PATH = CONFIG_DIR / ".secrets.toml"

# Default configuration files
config_files = [SETTINGS_PATH]
if SECRETS_PATH.exists():
    config_files.append(SECRETS_PATH)

# Allow overriding settings file via environment variable
if os.environ.get("SNOWPLOW_SETTINGS_FILE"):
    custom_settings = Path(os.environ["SNOWPLOW_SETTINGS_FILE"])
    if custom_settings.exists():
        config_files.append(custom_settings)

# Initialize dynaconf settings
dynaconf_settings = Dynaconf(
    envvar_prefix="SNOWPLOW",
    settings_files=config_files,
    env_switcher="SNOWPLOW_ENV",
    load_dotenv=True,
)

# Validate required settings
required_settings = [
    "common.service_name",
    "clickhouse.connection.host",
]

# Ensure all required settings are present
for setting in required_settings:
    if not dynaconf_settings.get(setting):
        parts = setting.split(".")
        parent = dynaconf_settings
        for i, part in enumerate(parts[:-1]):
            if part not in parent:
                parent[part] = {}
            parent = parent[part]

        if parts[-1] not in parent:
            # Set a default value or raise an error
            if setting == "common.service_name":
                parent[parts[-1]] = "simple-snowplow"
            elif setting == "clickhouse.connection.host":
                parent[parts[-1]] = "localhost"
            else:
                raise ValueError(f"Required setting {setting} is missing")

# Apply environment-specific overrides
env = os.environ.get("SNOWPLOW_ENV", "development")
if env == "production":
    # Safer defaults for production
    if dynaconf_settings.logging.level == "DEBUG":
        dynaconf_settings.logging.level = "INFO"

# Now define Pydantic models for type-checked settings


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


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""

    enabled: bool = dynaconf_settings.get("rate_limit.enabled", False)
    limit: int = dynaconf_settings.get("rate_limit.limit", 100)
    timeframe: int = dynaconf_settings.get("rate_limit.timeframe", 60)
    ip_whitelist: list[str] = dynaconf_settings.get(
        "rate_limit.ip_whitelist",
        [],
    )
    path_whitelist: list[str] = dynaconf_settings.get(
        "rate_limit.path_whitelist",
        ["/health"],
    )


class SecurityConfig(BaseSettings):
    """Security configuration."""

    disable_docs: bool = dynaconf_settings.get("security.disable_docs", False)
    trusted_hosts: list[str] = dynaconf_settings.get("security.trusted_hosts", ["*"])
    enable_https_redirect: bool = dynaconf_settings.get(
        "security.https_redirect",
        False,
    )
    trust_proxy_headers: bool = dynaconf_settings.get(
        "security.trust_proxy_headers",
        True,
    )
    rate_limiting: RateLimitConfig = RateLimitConfig()


class ElasticAPMConfig(BaseSettings):
    """ElasticAPM configuration."""

    enabled: bool = dynaconf_settings.get("elastic_apm.enabled", False)
    service_name: str = dynaconf_settings.get("common.service_name", "simple-snowplow")
    server_url: str | None = dynaconf_settings.get("elastic_apm.server_url")


class PrometheusConfig(BaseSettings):
    """Prometheus configuration."""

    enabled: bool = dynaconf_settings.get("prometheus.enabled", False)
    metrics_path: str = dynaconf_settings.get("prometheus.metrics_path", "/metrics/")


class SentryConfig(BaseSettings):
    """Sentry configuration."""

    enabled: bool = dynaconf_settings.get("sentry.enabled", False)
    dsn: str | None = dynaconf_settings.get("sentry.dsn")
    traces_sample_rate: float = dynaconf_settings.get("sentry.traces_sample_rate", 0.0)
    environment: str = dynaconf_settings.get("sentry.environment", "development")
    send_default_pii: bool = dynaconf_settings.get("sentry.send_default_pii", True)


class ProxyConfig(BaseSettings):
    """Proxy configuration for external domains."""

    domains: List[str] = dynaconf_settings.get(
        "proxy.domains",
        ["google-analytics.com", "www.googletagmanager.com"],
    )
    paths: List[str] = dynaconf_settings.get(
        "proxy.paths",
        ["analytics.js", "gtm.js"],
    )


class PerformanceConfig(BaseSettings):
    """Performance tuning configuration."""

    max_concurrent_connections: int = dynaconf_settings.get(
        "performance.max_concurrent_connections",
        100,
    )
    db_pool_size: int = dynaconf_settings.get(
        "performance.db_pool_size",
        5,
    )
    db_pool_overflow: int = dynaconf_settings.get(
        "performance.db_pool_overflow",
        10,
    )


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
    tables: dict[str, Any] = dynaconf_settings.get(
        "databases.clickhouse.tables",
        {},
    )


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
    sentry: SentryConfig = SentryConfig()
    proxy: ProxyConfig = ProxyConfig()
    performance: PerformanceConfig = PerformanceConfig()
    common: CommonConfig = CommonConfig()
    clickhouse: ClickHouseConfig = ClickHouseConfig()

    class Config:
        env_prefix = "SNOWPLOW_"
        case_sensitive = True


settings = Settings()

# Make original dynaconf settings available if needed
dynaconf = dynaconf_settings
