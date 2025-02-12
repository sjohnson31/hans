import sounddevice as sd
import numpy as np


class AudioDebugger:
    def __init__(self, playback_seconds=5, sample_rate: int = 16_000, dtype=np.int16):
        self.playback_seconds = playback_seconds
        self.sample_rate = sample_rate
        self.dtype = dtype
        self.audio_bytes = bytearray()

    def append(self, bytes: bytes | bytearray):
        self.audio_bytes.extend(bytes)
        trigger_size = self.playback_seconds * self.sample_rate * self.dtype.itemsize
        if len(self.audio_bytes) > trigger_size:
            print("Playing debug audio")
            sd.play(
                np.frombuffer(self.audio_bytes, self.dtype),
                samplerate=self.sample_rate,
                blocking=True,
            )
            self.audio_bytes = bytearray()
