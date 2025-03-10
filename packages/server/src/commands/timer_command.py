from datetime import datetime
from queue import Queue
import threading
import time

from durations_nlp import Duration
from durations_nlp.exceptions import ScaleFormatError

from src.commands.command import Command


def _make_duration_string(duration: Duration) -> str:
    if duration.to_minutes() < 1:
        return f'{int(duration.to_seconds())} second'
    minutes = int(duration.to_seconds() // 60)
    seconds = int(duration.to_seconds() % 60)
    return f'{minutes} minute and {seconds} second'


def dumb_timer(seconds: int, message_q: Queue, sender_addr: tuple[str, int]):
    time.sleep(seconds)
    message_q.put(('Your timer has expired', sender_addr))


class TimerCommand(Command):
    grammar_root: str = 'timer'
    grammar: str = """
    timer ::= "set a " ( duration " timer." | "timer for " duration ".")
    duration ::= duration-with-halves | duration-without-halves
    # e.g. an hour and a half or one and a half hour
    duration-with-halves ::= ( duration-half-first | duration-half-last )
    # e.g. 30 minutes or 1 hour and 30 minutes
    duration-without-halves ::= number " " time-unit (" and " number " " time-unit)?
    # e.g. one and a half hours
    duration-half-first ::= number " and a half " time-unit 
    # e.g. an hour and a half
    duration-half-last ::= ("a" | "an")? " " time-unit " and a half"
    time-unit ::= ("second" | "minute" | "hour") [s]?
    number ::= [0-9] [0-9]? [0-9]?
    """

    transcription_examples: list[str] = [
        'set a 5 minute timer.',
        'set a 15 hour and 3 minute timer.',
    ]

    def run(
        self, command_text: str, response_q: Queue[str], sender_addr: tuple[str, int]
    ) -> bool:
        if 'timer' not in command_text:
            return False

        duration_words = (
            command_text.removeprefix('set a ')
            .removeprefix('timer for ')
            .removesuffix('.')
            .removesuffix(' timer')
        )

        if 'and a half' in duration_words:
            if 'hour' in duration_words:
                addition = '30 minutes'
            elif 'minute' in duration_words:
                addition = '30 seconds'
            elif 'second':
                addition = '500 milliseconds'
            else:
                return False

            duration_words = (
                f'{duration_words.replace("and a half", "")} and {addition}'
            )
        try:
            duration = Duration(duration_words)
            print(f'Successfully found duration: {duration=}')
        except ScaleFormatError:
            print(f'Failed to get duration {duration_words}')
            return False

        dur_str = _make_duration_string(duration)
        print(f'Setting a timer for {dur_str} at {datetime.now()}')
        response_q.put((f'Setting a {dur_str} timer', sender_addr))
        t = threading.Thread(
            target=dumb_timer,
            args=[duration.to_seconds(), response_q, sender_addr],
            daemon=True,
        )
        t.start()
        return True
