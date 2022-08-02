from config import settings
from elasticapm.contrib.starlette import make_apm_client


elastic_config = settings.elastic_apm.copy()
elastic_enabled = elastic_config.pop("enabled")
elastic_config["SERVICE_NAME"] = settings.common.service_name

if elastic_enabled:
    elastic_apm_client = make_apm_client(elastic_config)
