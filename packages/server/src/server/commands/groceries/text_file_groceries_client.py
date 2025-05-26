import os

from server.commands.groceries.groceries_client import GroceriesClient


class TextFileGroceriesClient(GroceriesClient):
    def __init__(self, file_path: os.PathLike):
        self._file_path = file_path

    def add_to_shopping_list(self, item: str) -> None:
        with open(self._file_path, 'w+') as f:
            f.write(f'{item}\n')
        print(f'Wrote {item} to the grocery list')
