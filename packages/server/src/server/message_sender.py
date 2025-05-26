import asyncio
from typing import Any, NoReturn

import numpy as np
from transport.transport import AudioSegment


async def text_to_audio(
    text_q: asyncio.Queue[str], audio_q: asyncio.Queue[AudioSegment], tts: Any
) -> NoReturn:
    while True:
        text = await text_q.get()
        print(f'Got message {text}, sending to client')
        audio_raw = np.array(tts.tts(text=text), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        audio_norm_i16 = audio_norm.astype(np.int16)
        await audio_q.put(AudioSegment(audio=audio_norm_i16, sample_rate=48_000))
