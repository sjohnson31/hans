import asyncio
from collections.abc import AsyncIterator, Callable
from typing import NoReturn

import numpy as np
from numpy.typing import NDArray


class DisconnectedError(Exception):
    pass


async def read_audio_stream(
    reader: asyncio.StreamReader, buffer_size: int = 1024
) -> AsyncIterator[NDArray[np.int16]]:
    while True:
        data = await reader.read(buffer_size)
        yield np.frombuffer(data, dtype=np.int16)


async def write_audio_stream(
    writer: asyncio.StreamWriter, audio_stream: AsyncIterator[NDArray[np.int16]]
) -> None:
    async for audio_chunk in audio_stream:
        writer.write(audio_chunk.tobytes())
        await writer.drain()
    raise RuntimeError('Audio stream ended unexpectedly')


async def connect_to_server(
    host: str, port: int, audio_stream: AsyncIterator[NDArray[np.int16]]
) -> AsyncIterator[NDArray[np.int16]]:
    reader, writer = await asyncio.open_connection(host, port)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(write_audio_stream(writer, audio_stream))
        async for audio_chunk in read_audio_stream(reader):
            yield audio_chunk
        raise DisconnectedError()


async def write_queue(
    writer: asyncio.StreamWriter,
    queue: asyncio.Queue[NDArray[np.int16]],
) -> NoReturn:
    while True:
        audio_chunk = await queue.get()
        writer.write(audio_chunk.tobytes())
        await writer.drain()


async def serve(
    handle_client: Callable[
        [AsyncIterator[NDArray[np.int16]], asyncio.Queue[NDArray[np.int16]]], None
    ],
    host: str,
    port: int,
) -> NoReturn:
    async def handler_wrapper(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        async with asyncio.TaskGroup() as tg:
            write_q = asyncio.Queue[NDArray[np.int16]]()
            tg.create_task(write_queue(writer, write_q))
            tg.create_task(handle_client(read_audio_stream(reader), write_q))

    server = await asyncio.start_server(handler_wrapper, host, port)
    async with server:
        await server.serve_forever()

    raise RuntimeError('Server stopped unexpectedly')
