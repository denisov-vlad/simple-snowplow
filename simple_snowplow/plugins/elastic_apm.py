from core.config import settings
from elasticapm.contrib.starlette import make_apm_client

ELASTIC_APM_CONFIG = settings.elastic_apm

elastic_config = ELASTIC_APM_CONFIG.model_dump()
elastic_enabled = elastic_config.pop("enabled")
elastic_config["SERVICE_NAME"] = settings.common.service_name

if elastic_enabled:
    elastic_apm_client = make_apm_client(elastic_config)
