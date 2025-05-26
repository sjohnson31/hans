import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
import struct
from typing import Any, NoReturn

import numpy as np
from numpy.typing import NDArray

from transport.retry import retry_iterator_with_backoff, retry_with_backoff

HEADER_FMT = '<LL'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


class DisconnectedError(Exception):
    pass


@dataclass
class AudioSegment:
    sample_rate: int
    audio: NDArray[np.int16]


async def read_audio_stream(
    reader: asyncio.StreamReader, buffer_size: int = 1024
) -> AsyncIterator[AudioSegment]:
    received_bytes = bytearray()
    while True:
        data = await reader.read(buffer_size)
        received_bytes.extend(data)

        if len(received_bytes) < HEADER_SIZE:
            continue

        frame_num_bytes, sample_rate = struct.unpack_from(HEADER_FMT, received_bytes)
        if (len(received_bytes) - HEADER_SIZE) >= frame_num_bytes:
            audio_segment = received_bytes[HEADER_SIZE : HEADER_SIZE + frame_num_bytes]
            received_bytes = received_bytes[HEADER_SIZE + frame_num_bytes :]
            yield AudioSegment(
                audio=np.frombuffer(audio_segment, dtype=np.int16),
                sample_rate=sample_rate,
            )


async def write_audio_segment(
    writer: asyncio.StreamWriter, audio_segment: AudioSegment
) -> None:
    audio_bytes = audio_segment.audio.tobytes()
    frame = struct.pack(HEADER_FMT, len(audio_bytes), audio_segment.sample_rate)
    writer.write(frame + audio_bytes)
    await writer.drain()


async def write_audio_stream(
    writer: asyncio.StreamWriter, audio_stream: AsyncIterator[AudioSegment]
) -> None:
    try:
        async for audio_segment in audio_stream:
            await write_audio_segment(writer, audio_segment)
    except Exception as e:
        print(f"in writeaudio {e}")

    print("Audio stream ended, closing writer")
    raise RuntimeError('Audio stream ended unexpectedly')


async def connect_to_server(
    host: str,
    port: int,
    audio_stream: AsyncIterator[AudioSegment],
) -> AsyncIterator[AudioSegment]:
    async for audio_chunk in retry_iterator_with_backoff(
        func=_connect_to_server_once,
        host=host,
        port=port,
        audio_stream=audio_stream,
    ):
        yield audio_chunk


async def _connect_to_server_once(
    host: str, port: int, audio_stream: AsyncIterator[AudioSegment]
) -> AsyncIterator[AudioSegment]:
    reader, writer = await asyncio.open_connection(host, port)
    print("Connected to server at", (host, port))
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(write_audio_stream(writer, audio_stream))
            async for audio_chunk in read_audio_stream(reader):
                yield audio_chunk
            raise DisconnectedError()
    except Exception as e:
        print(e)
        writer.close()
        await writer.wait_closed()


async def write_queue(
    writer: asyncio.StreamWriter,
    queue: asyncio.Queue[AudioSegment],
) -> NoReturn:
    while True:
        audio_segment = await queue.get()
        await write_audio_segment(writer, audio_segment)


async def serve(
    handle_client: Callable[
        [AsyncIterator[AudioSegment], asyncio.Queue[AudioSegment]],
        Coroutine[Any, Any, None],
    ],
    host: str,
    port: int,
) -> NoReturn:
    await retry_with_backoff(_serve_once, handle_client, host, port)
    raise RuntimeError('Gave up serving, should not happen')

async def _serve_once(
    handle_client: Callable[
        [AsyncIterator[AudioSegment], asyncio.Queue[AudioSegment]],
        Coroutine[Any, Any, None],
    ],
    host: str,
    port: int,
) -> NoReturn:
    async def handler_wrapper(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        async with asyncio.TaskGroup() as tg:
            write_q = asyncio.Queue[AudioSegment]()
            tg.create_task(write_queue(writer, write_q))
            tg.create_task(handle_client(read_audio_stream(reader), write_q))

    server = await asyncio.start_server(handler_wrapper, host, port)
    async with server:
        await server.serve_forever()

    raise RuntimeError('Server stopped unexpectedly')
