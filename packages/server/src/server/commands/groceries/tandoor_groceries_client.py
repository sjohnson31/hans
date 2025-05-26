from urllib.parse import urljoin

import httpx

from server.commands.groceries.groceries_client import GroceriesClient


class TandoorGroceriesClient(GroceriesClient):
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def add_to_shopping_list(self, item: str) -> None:
        resp = httpx.post(
            urljoin(self.base_url, 'api/shopping-list-entry/'),
            json={'food': {'name': item}, 'amount': '1'},
            headers={'Authorization': f'Bearer {self.api_key}'},
        )
        if not 200 < resp.status_code < 300:
            # TODO: Better error handling
            raise RuntimeError(f'Failed : {resp.status_code} {resp.text}')
