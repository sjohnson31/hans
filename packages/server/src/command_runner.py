import queue
import re
import threading
import time
from typing import Any
from datetime import datetime
from durations_nlp import Duration
from durations_nlp.exceptions import ScaleFormatError
from number_parser import parse as replace_textual_numbers

# Have to replace the word "seconds", because number_parser
# will turn it into a number
SECONDS_UNITS_REPLACEMENT = '__SECONDS_UNITS__'


def make_duration_string(duration: Duration) -> str:
    if duration.to_minutes() < 1:
        return f'{int(duration.to_seconds())} second'
    minutes = int(duration.to_seconds() // 60)
    seconds = int(duration.to_seconds() % 60)
    return f'{minutes} minute and {seconds} second'


def run_command(command_text: str, message_q: queue.Queue, sender_addr: Any) -> bool:
    return run_timer_command(command_text, message_q, sender_addr)


def dumb_timer(seconds: int, message_q: queue.Queue, sender_addr: Any):
    time.sleep(seconds)
    message_q.put(('Your timer has expired', sender_addr))


def run_timer_command(
    command_text: str, message_q: queue.Queue, sender_addr: Any
) -> bool:
    command_text = replace_textual_numbers(
        command_text.replace('-', ' ')
        .replace('.', '')
        .replace('second', SECONDS_UNITS_REPLACEMENT)
    )
    match = re.search('\d', command_text)
    if not match:
        return False
    start, _ = match.span()
    match = re.search('time[r]?', command_text)
    if not match:
        return False
    end, _ = match.span()

    if start >= end:
        print(f'Failed {start=}, {end=}')
        return False

    try:
        duration_words = command_text[start:end].replace(
            SECONDS_UNITS_REPLACEMENT, 'second'
        )
        print(f'Success {duration_words=}')
        duration = Duration(duration_words)
        print(f'Double success {duration=}')
    except ScaleFormatError:
        print('Failed to get duration')
        return False

    dur_str = make_duration_string(duration)
    print(f'Setting a timer for {dur_str} at {datetime.now()}')
    message_q.put((f'Setting a {dur_str} timer', sender_addr))
    t = threading.Thread(
        target=dumb_timer,
        args=[duration.to_seconds(), message_q, sender_addr],
        daemon=True,
    )
    t.start()
    return True
