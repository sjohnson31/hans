from asyncio import CancelledError
from collections.abc import AsyncIterator, Awaitable, Callable
import time
from typing import ParamSpec, TypeVar

MAX_SLEEP_SECS = 5
STARTING_SLEEP_SECS = 0.1


_R = TypeVar('_R')
_P = ParamSpec('_P')


class RetryCancelledError(Exception):
    pass


async def retry_with_backoff(
    func: Callable[_P, Awaitable[_R]],
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _R:
    """Retry a function with exponential backoff."""
    print('Start retry with backoff')
    retries = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except CancelledError as e:
            print('Retry cancelled, cancelling retry')
            raise RetryCancelledError() from e
        except KeyboardInterrupt as e:
            print('Keyboard interrupt, cancelling retry')
            raise RetryCancelledError() from e
        except Exception as e:
            print('Failed to connect, retrying: ', e)
            timeout = STARTING_SLEEP_SECS * (2**retries)
            sleep_secs = min(timeout, MAX_SLEEP_SECS)
            time.sleep(sleep_secs)
            if timeout < MAX_SLEEP_SECS:
                retries += 1


async def retry_iterator_with_backoff(
    func: Callable[_P, AsyncIterator[_R]], *args: _P.args, **kwargs: _P.kwargs
) -> AsyncIterator[_R]:
    """Retry a generator with exponential backoff."""
    retries = 0
    while True:
        try:
            async for item in func(*args, **kwargs):
                yield item
        except CancelledError as e:
            print('Retry cancelled, cancelling retry')
            raise RetryCancelledError() from e
        except KeyboardInterrupt as e:
            print('Keyboard interrupt, cancelling retry')
            raise RetryCancelledError() from e
        except Exception as e:
            print(e)
            timeout = STARTING_SLEEP_SECS * (2**retries)
            sleep_secs = min(timeout, MAX_SLEEP_SECS)
            time.sleep(sleep_secs)
            if timeout < MAX_SLEEP_SECS:
                retries += 1
