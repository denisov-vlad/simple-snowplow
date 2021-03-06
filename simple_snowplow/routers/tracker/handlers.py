import elasticapm
from routers.tracker import snowplow
from routers.tracker.useragent import parse_agent


@elasticapm.async_capture_span()
async def process_data(body, user_agent, user_ip, cookies):
    base = {"user_ip": user_ip}
    if user_agent:
        ua_data = await parse_agent(user_agent)
        base = dict(base, **ua_data)

    try:
        data = body.data
    except AttributeError:
        data = [body]

    result = []

    for i in data:
        payload_data = await snowplow.parse_payload(i, cookies)
        item_data = dict(base, **payload_data)

        result.append(item_data)

    return result
