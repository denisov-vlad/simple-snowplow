from fastapi import Query
from pydantic import AnyUrl, BaseModel


class HashModel(BaseModel):
    url: AnyUrl = Query(..., title="URL to hash")
