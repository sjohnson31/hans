import asyncio

from server.commands.command import Command
from server.commands.groceries.groceries_client import GroceriesClient


class AddToGroceryListCommand(Command):
    grammar_root: str = 'add-to-grocery-list'
    grammar: str = """
    add-to-grocery-list ::= "add " [^\n]+ " to the grocery list."
    """

    transcription_examples: list[str] = [
        'add an eggplant to the grocery list.',
    ]

    def __init__(self, groceries_client: GroceriesClient):
        self.groceries_client = groceries_client

    async def run(
        self, command_text: str, response_q: asyncio.Queue[str]
    ) -> bool:
        if not command_text.endswith(' to the grocery list.'):
            return False

        item = command_text.removeprefix('add ').removesuffix(' to the grocery list.')

        print(f'Adding {item} to the grocery list')
        self.groceries_client.add_to_shopping_list(item)

        await response_q.put(f'Added {item}.')
        return True
