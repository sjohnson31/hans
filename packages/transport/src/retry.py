from collections.abc import Callable, Generator
import multiprocessing as mp
import time
from typing import ParamSpec, TypeVar

MAX_SLEEP_SECS = 5
STARTING_SLEEP_SECS = 0.1


_R = TypeVar('_R')
_P = ParamSpec('_P')


class RetryCancelledError(Exception):
    pass


def retry_with_backoff(
    retry_err_q: mp.Queue, func: Callable[_P, _R], *args: _P.args, **kwargs: _P.kwargs
) -> _R:
    """Retry a function with exponential backoff."""
    print('Start retry with backoff')
    retries = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print('Failed to connect, retrying: ', e)
            if not retry_err_q.empty:
                raise RetryCancelledError() from e
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
