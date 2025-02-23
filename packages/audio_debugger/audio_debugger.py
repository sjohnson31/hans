from enum import Enum
import sounddevice as sd
import numpy as np
from numpy._typing import DTypeLike
import wave


class DebugMode(Enum):
    PLAYBACK = ('playback',)
    SAVE = 'save'


class AudioDebugger:
    def __init__(
        self,
        playback_seconds = 5,
        sample_rate: int = 16_000,
        dtype: DTypeLike = np.int16,
        mode=DebugMode.PLAYBACK,
    ):
        self.playback_seconds = playback_seconds
        self.sample_rate = sample_rate
        # Coerce dtypelike to actual dtype
        self.dtype = np.dtype(dtype)
        self.audio_bytes = bytearray()
        self.mode = mode
        self.debug_count = 0

    def append(self, audio_bytes: bytes | bytearray):
        self.audio_bytes.extend(audio_bytes)
        trigger_size = self.playback_seconds * self.sample_rate * self.dtype.itemsize
        if len(self.audio_bytes) > trigger_size:
            if self.mode == DebugMode.PLAYBACK:
                print('Playing debug audio')
                sd.play(
                    np.frombuffer(self.audio_bytes, self.dtype),
                    samplerate=self.sample_rate,
                    blocking=True,
                )
                self.audio_bytes = bytearray()
            else:
                print('Saving debug audio')
                with wave.open(
                    f'debug/debug_audio_{self.debug_count}.wav', 'wb'
                ) as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(self.dtype.itemsize)
                    wav.setframerate(self.sample_rate)
                    wav.writeframes(self.audio_bytes)
                self.debug_count += 1
                self.audio_bytes = bytearray()
