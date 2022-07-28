from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="SNOWPLOW",
    settings_files=["settings.toml", ".secrets.toml"],
)
