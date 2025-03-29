from collections.abc import Callable, Generator
import time
from typing import ParamSpec, TypeVar

MAX_SLEEP_SECS = 5
STARTING_SLEEP_SECS = 0.1


_R = TypeVar('_R')
_P = ParamSpec('_P')


def retry_with_backoff(func: Callable[_P, _R], *args: _P.args) -> _R:
    """Retry a function with exponential backoff."""
    retries = 0
    while True:
        try:
            return func(*args)
        except Exception as e:
            print(e)
            sleep_secs = min(STARTING_SLEEP_SECS * (2**retries), MAX_SLEEP_SECS)
            time.sleep(sleep_secs)
            retries += 1


def retry_generator_with_backoff(
    func: Callable[_P, Generator[_R, None, None]], *args: _P.args
) -> Generator[_R, None, None]:
    """Retry a generator with exponential backoff."""
    retries = 0
    while True:
        try:
            yield from func(*args)
        except Exception as e:
            print(e)
            timeout = STARTING_SLEEP_SECS * (2**retries)
            sleep_secs = min(timeout, MAX_SLEEP_SECS)
            time.sleep(sleep_secs)
            if timeout < MAX_SLEEP_SECS:
                retries += 1
