from dataclasses import dataclass
from queue import Queue

from src.commands.command import Command


@dataclass
class Location:
    origin_stop_id: str
    name: str
    allowed_route_ids: str


class NextBusCommand(Command):
    grammar_root = 'next-bus'

    def __init__(self, locations: list[Location]):
        options = ' | '.join([f'"{loc.name}"' for loc in locations])
        self.grammar = f"""
            {self.grammar_root} ::= "when is the next bus to " ({options}) "?"
        """
        self.transcription_examples = [
            f'when is the next bus to {loc}?' for loc in locations
        ]

    def run(self, command_text: str, response_q: Queue[str]) -> bool:
        """
        Execute the command specified in the command_text

        :param command_text: the command to be executed,
                             it is not guaranteed to match your grammar
        :param response_q: Any responses to the command should be put in this queue
                           to be read aloud in the client

        :returns: False if the command is not recognized,
                  True if the command is recognized
        """
        raise NotImplementedError()
