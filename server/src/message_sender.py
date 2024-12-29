import queue
import socket
from typing import NoReturn


def send_audio_message(message_q: queue.Queue, sock: socket.socket) -> NoReturn:
    while True:
        message, sender_addr = message_q.get()
        print(f'Got message {message}, sending to client')
        print(f'{sender_addr=}')
        sock.sendto(message.encode(), sender_addr)
