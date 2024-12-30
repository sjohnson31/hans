import queue
import socket
import struct
from typing import NoReturn

import numpy as np


def send_audio_message(message_q: queue.Queue, sock: socket.socket, tts) -> NoReturn:
    while True:
        message, _ = message_q.get()
        print(f'Got message {message}, sending to client')
        audio_raw = np.array(tts.tts(text=message), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        b_audio = audio_norm.astype(np.int16).tobytes()
        sock.send(struct.pack('<L', len(b_audio)))
        sock.sendall(b_audio)
