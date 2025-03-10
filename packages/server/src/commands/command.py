from queue import Queue
from typing import Protocol


class Command(Protocol):
    grammar_root: str
    """Name of the root node in your grammar"""

    grammar: str
    """
    Backus–Naur form grammar for commands
    https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form
    """

    transcription_examples: list[str]
    """
    Transcription examples for expected voice commands
    Used by whispercpp to guide transcription
    https://github.com/ggerganov/whisper.cpp/blob/cadfc50eabb46829a0d5ac7ffcb3778ad60a1257/include/whisper.h#L516
    """

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
