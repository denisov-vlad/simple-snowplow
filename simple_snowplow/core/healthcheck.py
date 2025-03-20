from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.status import HTTP_502_BAD_GATEWAY

async def probe(request: Request):
    query = await request.app.state.ch_client.query("SELECT 1")
    ch_status = query.first_row[0] == 1

    status = {"clickhouse": ch_status}
    status = jsonable_encoder(status)

    for v in status.values():
        if not v:
            return JSONResponse(content=status, status_code=HTTP_502_BAD_GATEWAY)

    result = JSONResponse(
        content={"status": status, "table": await request.app.state.connector.get_table_name()},
    )

    return result 