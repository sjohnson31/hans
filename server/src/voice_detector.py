from silero_vad import VADIterator
import numpy as np
import torch

SAMPLING_RATE=16000
CONFIDENCE_CUTOFF = .6


class VoiceDetector:
    def __init__(self, model):
        self._model = model

    def big_chunk_is_voice(self, big_chunk: bytes) -> bool:
        if (len(big_chunk) % 1024 != 0):
            raise RuntimeError('Chunks must be a multiple of 1024 bytes')

        for i in range(0, len(big_chunk), 1024):
            if self._chunk_is_voice(big_chunk[i:i+1024]):
                return True
        return False

    def _chunk_is_voice(self, chunk: bytes) -> bool:
        if len(chunk) != 1024:
            raise RuntimeError('Chunks must be exactly 1024 bytes')

        torch_chunk = torch.from_numpy(np.frombuffer(chunk, np.int16))

        speech_prob = self._model(torch_chunk, SAMPLING_RATE).item()
        return speech_prob > CONFIDENCE_CUTOFF
