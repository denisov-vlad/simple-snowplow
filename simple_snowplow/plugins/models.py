import logging
from typing import Any
from typing import Type

from plugins import elastic_apm
from pydantic import BaseModel
from pydantic import ValidationError

logger = logging.getLogger("validator")


class LoggerBaseModel(BaseModel):
    """
    Helps to debug validation errors
    """

    @classmethod
    def validate(cls: Type["Model"], value: Any) -> "Model":
        try:
            return super().validate(value)
        except ValidationError as e:
            if elastic_apm.elastic_enabled:
                elastic_apm.elastic_apm_client.capture_exception()
            logger.warning(
                f"Validation error for {cls.__name__} \n"
                + f"error: {e.errors()} \n data: {value}"
            )
            raise e
