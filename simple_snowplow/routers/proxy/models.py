from fastapi import Query
from pydantic import BaseModel, AnyUrl


class HashModel(BaseModel):
    url: AnyUrl = Query(..., title="URL to hash")