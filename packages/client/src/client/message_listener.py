from collections.abc import Callable
import multiprocessing as mp
from types import NoneType
from typing import NoReturn


def listen(play_cb: Callable[[bytes], NoneType], message_q: mp.Queue) -> NoReturn:
    while True:
        message = message_q.get()
        play_cb(message)
