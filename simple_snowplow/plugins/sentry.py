from core.config import settings

SENTRY_CONFIG = settings.sentry

sentry_config = SENTRY_CONFIG.model_dump()
sentry_enabled = sentry_config.pop("enabled")
