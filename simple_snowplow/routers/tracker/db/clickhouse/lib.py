import requests
from aiochclient import ChClient


class ChClientBulk(ChClient):
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
