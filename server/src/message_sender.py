import queue
import socket
import struct
from typing import Dict, NoReturn

import numpy as np


def send_audio_message(message_q: queue.Queue, tts) -> NoReturn:
    socks: Dict[str, socket.socket] = {}
    while True:
        message, remote_addr = message_q.get()
        if remote_addr not in socks.keys():
            try:
                socks[remote_addr] = socket.create_connection(remote_addr, timeout=1.0)
            except TimeoutError:
                print(f'Failed to connect to host {remote_addr}')
                continue
            except ConnectionRefusedError:
                print(f'Remote host {remote_addr} refused connection')
                continue
            except socket.gaierror:
                print(f'Failed name resolution for remote host {remote_addr}')
                continue
        sock = socks.get(remote_addr)
        print(f'Got message {message}, sending to client')
        audio_raw = np.array(tts.tts(text=message), dtype=np.float32)
        audio_norm = audio_raw * (32767 / max(0.01, np.max(np.abs(audio_raw))))
        b_audio = audio_norm.astype(np.int16).tobytes()
        sock.send(struct.pack('<L', len(b_audio)))
        sock.sendall(b_audio)
