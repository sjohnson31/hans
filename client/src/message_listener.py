import socket
import struct
from types import NoneType
from typing import Callable, NoReturn


def listen(play_cb: Callable[[bytes], NoneType], port: int) -> NoReturn:
    while True:
        inner_listen(play_cb, port)


def inner_listen(play_cb: Callable[[bytes], NoneType], port: int) -> None:
    udp_ip = '0.0.0.0'
    udp_port = port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((udp_ip, udp_port))
        sock.listen(1)
        conn, addr = sock.accept()
        print('Socket connected')

        with conn:
            audio_buf = bytearray()
            message_size = -1
            while True:
                message = conn.recv(4096)
                if len(message) == 0:
                    print('Socket disconnected')
                    return
                print('Got a message')
                if message_size == -1:
                    message_size = struct.unpack_from('<L', message)[0]
                    print(f'Start getting new message: {message_size=}')
                    message = message[4:]

                if message_size - len(audio_buf) > len(message):
                    audio_buf.extend(message)
                else:
                    audio_buf.extend(message[:message_size - len(audio_buf)])
                    message_size = -1
                    print('Done getting message')
                    play_cb(bytes(audio_buf))
                    audio_buf = bytearray()
