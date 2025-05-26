import asyncio
import queue
from typing import NoReturn

import numpy as np
from transport2 import AudioSegment


def send_audio_message(
    message_q: queue.Queue, tts, out_q: np.ndarray[np.int16]
) -> NoReturn:
    while True:
        message = message_q.get()
        print(f'Got message {message}, sending to client')
        audio_raw = np.array(tts.tts(text=message), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        audio_norm_i16 = audio_norm.astype(np.int16)
        out_q.put(audio_norm_i16)


async def text_to_audio(
    text_q: asyncio.Queue[str], audio_q: asyncio.Queue[AudioSegment], tts
) -> NoReturn:
    while True:
        text = await text_q.get()
        print(f'Got message {text}, sending to client')
        audio_raw = np.array(tts.tts(text=text), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        audio_norm_i16 = audio_norm.astype(np.int16)
        await audio_q.put(AudioSegment(audio=audio_norm_i16, sample_rate=48_000))
