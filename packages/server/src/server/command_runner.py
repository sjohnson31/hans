import asyncio
import itertools

from server.commands.command import Command


class CommandRunner:
    def __init__(self, commands: list[Command]):
        self.commands = commands
        self.grammar_root = 'root'

        # In python 3.11, you cannot use backslashes in fstrings.
        # We can remove this once we migrate to 3.12 or higher
        nl = '\n'
        self.grammar = f"""
        root ::= wake " " command
        wake ::= "Hey Hans,"
        command ::= ( {' | '.join([cmd.grammar_root for cmd in self.commands])} )
        {nl.join([cmd.grammar for cmd in self.commands])}
        """

        examples = itertools.chain(
            *[cmd.transcription_examples for cmd in self.commands]
        )
        self.initial_prompt = '\n'.join(
            [f'Hey Hans, {example}' for example in examples]
        )

    async def run(
        self,
        command_text: str,
        message_q: asyncio.Queue[str],
    ) -> None:
        command_text = command_text.removeprefix('Hey Hans, ')
        for command in self.commands:
            if await command.run(command_text, message_q):
                break
