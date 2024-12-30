import os
import socket
import struct
from types import NoneType
from typing import Callable, NoReturn
import wave

MAX_PACKET_SIZE = 65_507


def write_audio(frames):
    channels = 1
    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(frames)


def listen(play_cb: Callable[..., NoneType]) -> NoReturn:
    while True:
        inner_listen(play_cb)


def inner_listen(play_cb: Callable[..., NoneType]) -> None:
    udp_ip = '0.0.0.0'
    udp_port = int(os.environ['SERVER_PORT'])
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
                    #write_audio(audio_buf)
                    play_cb(bytes(audio_buf))
