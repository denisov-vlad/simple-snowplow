import os
from pathlib import Path

from dynaconf import Dynaconf

# Base configuration path
CONFIG_DIR = Path(__file__).parent
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

settings = Dynaconf(
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
    if not settings.get(setting):
        parts = setting.split(".")
        parent = settings
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
    if settings.logging.level == "DEBUG":
        settings.logging.level = "INFO"
