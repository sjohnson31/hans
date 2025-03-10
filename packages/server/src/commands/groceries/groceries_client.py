from typing import Protocol


class GroceriesClient(Protocol):
    def add_to_shopping_list(self, item: str) -> None:
        raise NotImplementedError()
