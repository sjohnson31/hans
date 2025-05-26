import enum
from enum import Enum
import os
import wave

import numpy as np
from numpy._typing import DTypeLike
import sounddevice as sd


class DebugMode(Enum):
    PLAYBACK = enum.auto()
    SAVE = enum.auto()


class AudioDebugger:
    def __init__(
        self,
        playback_seconds: float=5,
        sample_rate: int = 16_000,
        dtype: DTypeLike = np.int16,
        mode: DebugMode=DebugMode.PLAYBACK,
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
                os.makedirs('debug', exist_ok=True)
                with wave.open(
                    f'debug/debug_audio_{self.debug_count}.wav', 'wb'
                ) as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(self.dtype.itemsize)
                    wav.setframerate(self.sample_rate)
                    wav.writeframes(self.audio_bytes)
                self.debug_count += 1
                self.audio_bytes = bytearray()
