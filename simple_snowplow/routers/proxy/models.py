from fastapi import Query
from pydantic import AnyUrl
from pydantic import BaseModel


class HashModel(BaseModel):
    url: AnyUrl = Query(..., title="URL to hash")
