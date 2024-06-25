import orjson as json_
import requests
from aiochclient import ChClient
from aiochclient.http_clients.abc import HttpClientABC


class ChClientBulk(ChClient):
    def __init__(
        self,
        session=None,
        url: str = "http://localhost:8123/",
        user: str = None,
        password: str = None,
        database: str = "default",
        compress_response: bool = False,
        json=json_,
        **settings,
    ):
        super().__init__(
            session,
            url,
            user,
            password,
            database,
            compress_response,
            json,
            **settings,
        )
        _http_client = HttpClientABC.choose_http_client(session)
        self._http_client = _http_client(session)
        self.url = url
        self.params = {}
        self.headers = {}
        if user:
            self.params["user"] = user
        if password:
            self.params["password"] = password
        if database:
            self.params["database"] = database
        if compress_response:
            self.params["enable_http_compression"] = 1
        self._json = json
        self.params.update(settings)

    async def is_alive(self) -> bool:
        """Checks if connection is Ok.

        Usage:

        .. code-block:: python

            assert await client.is_alive()

        :return: True if connection Ok. False instead.
        """

        response = requests.get(f"{self.url}/status")
        if not response.ok:
            return False

        response = response.json()
        if response["status"] == "ok":
            return True
        else:
            return False
