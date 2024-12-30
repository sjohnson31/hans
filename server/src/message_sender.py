import queue
import socket
import struct
from typing import NoReturn
import wave

import numpy as np


def write_audio(frames):
    channels = 1
    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames)


def send_audio_message(message_q: queue.Queue, sock: socket.socket, tts) -> NoReturn:
    while True:
        message, sender_addr = message_q.get()
        print(f'Got message {message}, sending to client')
        audio_raw = np.array(tts.tts(text=message), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        b_audio = audio_norm.astype(np.int16).tobytes()
        write_audio(b_audio)
        sock.send(struct.pack('<L', len(b_audio)))
        sock.sendall(b_audio)
