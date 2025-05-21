import asyncio
from collections.abc import AsyncIterator
import os

import librosa
import numpy as np
from numpy.typing import NDArray
import sounddevice as sd
from transport2 import connect_to_server


def main():
    asyncio.run(amain())


async def amain():
    server_ip = os.environ['SERVER_ADDRESS']
    server_port = int(os.environ['SERVER_PORT'])
    # Substring of the full device name given in sd.query_devices()
    # See https://python-sounddevice.readthedocs.io/en/0.5.1/api/streams.html#sounddevice.Stream
    # device parameter for more information
    input_device = os.environ.get('INPUT_DEVICE', sd.default.device[0])
    output_device = os.environ.get('OUTPUT_DEVICE', sd.default.device[1])

    input_sample_rate = int(
        sd.query_devices(input_device, 'input')['default_samplerate']
    )
    loop = asyncio.get_event_loop()
    input_q: asyncio.Queue[NDArray[np.int16]] = asyncio.Queue()

    async def stream_audio(audio_q: asyncio.Queue[NDArray[np.int16]]) -> AsyncIterator[NDArray[np.int16]]:
        while True:
            yield await audio_q.get()

    def input_cb(in_data: NDArray[np.float32], *_):
        new_sample = librosa.resample(
            in_data,
            orig_sr=input_sample_rate,
            target_sr=16_000,
            res_type='soxr_qq',
            axis=0,
        )
        resampled = (new_sample * np.iinfo(np.int16).max).astype(np.int16)
        loop.call_soon_threadsafe(input_q.put_nowait, resampled)

    def play_audio(audio_data: NDArray[np.int16]):
        sd.play(
            audio_data,
            # This is the samplerate coming out of the TTS
            # TODO: Encode samplerate in transport packet
            samplerate=48_000,
            device=output_device,
            blocking=True,
        )

    with sd.InputStream(
        device=input_device,
        channels=1,
        callback=input_cb,
        samplerate=input_sample_rate,
    ):
        async for audio_chunk in connect_to_server(server_ip, server_port, stream_audio(input_q)):
            play_audio(audio_chunk)


if __name__ == '__main__':
    main()
