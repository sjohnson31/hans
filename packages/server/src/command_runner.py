import itertools
import queue

from src.commands.command import Command
from src.commands.timer_command import TimerCommand

COMMANDS: list[Command] = [TimerCommand()]

# In python 3.11, you cannot use backslashes in fstrings.
# We can remove this once we migrate to 3.12 or higher
_NEWLINE = '\n'
GRAMMAR = f"""
root ::= wake " " command
wake ::= "Hey Hans,"
command ::= ( {' | '.join([cmd.grammar_root for cmd in COMMANDS])} )
{_NEWLINE.join([cmd.grammar for cmd in COMMANDS])}
"""

GRAMMAR_ROOT = 'root'

# Transcription examples for expected voice commands
# Used by whispercpp to guide transcription
# https://github.com/ggerganov/whisper.cpp/blob/cadfc50eabb46829a0d5ac7ffcb3778ad60a1257/include/whisper.h#L516
_ALL_TRAINING_SENTENCES = itertools.chain(
    *[cmd.transcription_examples for cmd in COMMANDS]
)
INITIAL_PROMPT = '\n'.join(
    [f'Hey Hans, {sentence}' for sentence in _ALL_TRAINING_SENTENCES]
)


def run_command(
    command_text: str, message_q: queue.Queue, sender_addr: tuple[str, int]
) -> None:
    command_text = command_text.removeprefix('Hey Hans, ')
    for command in COMMANDS:
        if command.run(command_text, message_q, sender_addr):
            break
