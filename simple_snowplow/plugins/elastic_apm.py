import logging
from typing import Any
from typing import Type

from config import settings
from elasticapm.contrib.starlette import make_apm_client
from pydantic import BaseModel
from pydantic import ValidationError
from pydantic.main import Model


elastic_config = settings.elastic_apm
_ = elastic_config.pop("enabled")
elastic_config["SERVICE_NAME"] = settings.common.service_name


elastic_apm_client = make_apm_client(elastic_config)


logger = logging.getLogger("validator")


class LoggerBaseModel(BaseModel):
    @classmethod
    def validate(cls: Type["Model"], value: Any) -> "Model":
        try:
            return super().validate(value)
        except ValidationError as e:
            elastic_apm_client.capture_exception()
            logger.warning(
                f"Validation error for {cls.__name__} \n"
                + f"error: {e.errors()} \n data: {value}"
            )
            raise e
