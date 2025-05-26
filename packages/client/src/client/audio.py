import asyncio
from typing import Any

import numpy as np
from numpy.typing import NDArray
import sounddevice as sd


async def play_buffer(
    buffer: NDArray[np.int16], sample_rate: int, output_device: Any
) -> None:
    loop = asyncio.get_event_loop()
    event = asyncio.Event()
    idx = 0

    def callback(
        outdata: NDArray[np.int16], frame_count: int, _, status: sd.CallbackFlags
    ):
        nonlocal idx
        if status:
            print(f'Audio Playback Warning: {status=}')
        remainder = len(buffer) - idx
        if remainder == 0:
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        valid_frames = frame_count if remainder >= frame_count else remainder
        outdata[:valid_frames] = buffer[idx : idx + valid_frames]
        outdata[valid_frames:] = 0
        idx += valid_frames

    if buffer.ndim == 1:
        buffer = buffer.reshape(buffer.shape[0], 1)
    stream = sd.OutputStream(
        callback=callback,
        dtype=buffer.dtype,
        channels=buffer.shape[1],
        samplerate=sample_rate,
        device=output_device,
    )
    with stream:
        await event.wait()
