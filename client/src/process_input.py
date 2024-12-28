import queue
import socket
import struct
from typing import NoReturn


def send_audio_frames(frame_q: queue.Queue, server_sock: socket.socket, server_addr: str, server_port: int) -> NoReturn:
    frame_len = 0
    fmt = ''
    frame_num = 0
    while True:
        frame = frame_q.get()
        if len(frame) != frame_len:
            frame_len = len(frame)
            fmt = f'<L{frame_len}h'
        print('Got frame, sending')
        server_sock.sendto(struct.pack(fmt, frame_num, *frame), (server_addr, server_port))
