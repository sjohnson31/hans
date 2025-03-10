from datetime import datetime
import queue
import threading
import time
from typing import Any

from durations_nlp import Duration
from durations_nlp.exceptions import ScaleFormatError


def make_duration_string(duration: Duration) -> str:
    if duration.to_minutes() < 1:
        return f'{int(duration.to_seconds())} second'
    minutes = int(duration.to_seconds() // 60)
    seconds = int(duration.to_seconds() % 60)
    return f'{minutes} minute and {seconds} second'


def run_command(command_text: str, message_q: queue.Queue, sender_addr: Any) -> bool:
    command_text = command_text.removeprefix('Hey Hans, ')
    return run_timer_command(command_text, message_q, sender_addr)


def dumb_timer(seconds: int, message_q: queue.Queue, sender_addr: Any):
    time.sleep(seconds)
    message_q.put(('Your timer has expired', sender_addr))


def run_timer_command(
    command_text: str, message_q: queue.Queue, sender_addr: Any
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

        duration_words = f'{duration_words.replace("and a half", "")} and {addition}'
    try:
        duration = Duration(duration_words)
        print(f'Successfully found duration: {duration=}')
    except ScaleFormatError:
        print(f'Failed to get duration {duration_words}')
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
