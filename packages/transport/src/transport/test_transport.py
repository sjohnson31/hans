from __future__ import annotations

from asyncio import TaskGroup
import asyncio
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import multiprocessing as mp
from os.path import dirname
from pathlib import Path
import queue
import socket
from tempfile import NamedTemporaryFile
import threading
import time
from typing import AsyncIterator

import numpy as np
import pytest

from transport.transport import AudioSegment, connect_to_server, serve


@pytest.fixture
def resource_path():
    return Path(dirname(__file__)).joinpath('../../resources').resolve()


@pytest.fixture(scope='module')
def unused_port() -> int:
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

async def die():
    raise RuntimeError('Ahhh! I am dying!')

@pytest.mark.asyncio
async def test_transport(unused_port: int):
    print(unused_port)

    server_message = b'Sent from server'
    client_message = b'Sent from client'

    received_from_client = bytearray()
    received_from_server = bytearray()

    async def client_audio_stream() -> AsyncIterator[AudioSegment]:
        yield AudioSegment(
            audio=np.frombuffer(client_message, dtype=np.int16),
            sample_rate=16000,
        )
        while True:
            await asyncio.sleep(0.1)

    async def handle_client(
        audio_stream: AsyncIterator[AudioSegment], out_q: asyncio.Queue[AudioSegment]
    ) -> None:
        await out_q.put(
            AudioSegment(
                audio=np.frombuffer(server_message, dtype=np.int16),
                sample_rate=16000,
            )
        )
        async for audio_segment in audio_stream:
            received_from_client.extend(audio_segment.audio.tobytes())
            print(f'Received from client: {len(received_from_client)} bytes')
            if (len(received_from_client) >= len(client_message)):
                raise StopAsyncIteration()

    async def collect_server_audio(port: int):
        async for audio_segment in connect_to_server(
            host='localhost',
            port=port,
            audio_stream=client_audio_stream(),
        ):
            received_from_server.extend(audio_segment.audio.tobytes())
            print(f'Received from server: {len(received_from_server)} bytes')
            if (len(received_from_server) >= len(server_message)):
                raise StopAsyncIteration()


    try:
        async with TaskGroup() as tg:
            try:
                async with asyncio.timeout(1):
                    tg.create_task(
                        serve(
                            handle_client=handle_client,
                            host='localhost',
                            port=unused_port,
                        )
                    )
                    tg.create_task(collect_server_audio(unused_port))
            except TimeoutError:
                print('Timeout occurred, stopping tasks')
                tg.create_task(die())
    except:
        print('Tasks completed or stopped due to an error')

    assert received_from_client == client_message
    assert received_from_server == server_message
