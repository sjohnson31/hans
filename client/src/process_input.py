import queue
import socket
import struct
from threading import Event
from typing import NoReturn

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2

CHUNK_SIZE = 4096

def send_audio_frames(frame_q: queue.Queue, server_sock: socket.socket, server_addr: str, server_port: int) -> NoReturn:
    frame_num = 0
    audio_data = bytearray()

    fmt = f'<hLH{CHUNK_SIZE}h'

    while True:
        frame = frame_q.get()
        audio_data.extend(frame)
        if (len(audio_data) > CHUNK_SIZE):
            print(f'Got frame, sending')

            chunk = audio_data[:CHUNK_SIZE]
            audio_data = audio_data[CHUNK_SIZE:]

            server_sock.sendto(struct.pack(fmt, FRAME_INDICATOR, frame_num, CHUNK_SIZE, *chunk), (server_addr, server_port))

            if frame_num >= MAX_COUNTER:
                frame_num = 0
            else:
                frame_num += 1
