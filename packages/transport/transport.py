from collections.abc import Generator
from dataclasses import dataclass
import queue
import socket
import ssl
import struct
from typing import NoReturn

from src.retry import retry_generator_with_backoff, retry_with_backoff

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2
MAX_PACKET_SIZE = 65_507
AUDIO_CHUNK_SIZE = 4096

HEADER_FMT = '<hH'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


@dataclass
class ClientAudioPacket:
    sender_addr: tuple[str, int]
    # signed i16 pcm audio data
    audio_bytes: bytes


def stream_client_audio(
    audio_frame_q: queue.Queue[bytes], addr: str, port: str
) -> NoReturn:
    return retry_with_backoff(_stream_client_audio, audio_frame_q, addr, port)


def _stream_client_audio(
    audio_frame_q: queue.Queue[bytes], addr: str, port: str
) -> NoReturn:
    context = ssl.create_default_context()
    with (
        socket.create_connection((addr, port), timeout=1.5) as unsecured_sock,
        context.wrap_socket(unsecured_sock, server_hostname=addr) as sock,
    ):
        audio_data = bytearray()
        fmt = f'{HEADER_FMT}{AUDIO_CHUNK_SIZE}h'

        while True:
            frame = audio_frame_q.get()
            audio_data.extend(frame)
            if len(audio_data) > AUDIO_CHUNK_SIZE:
                print('Got frame, sending')

                chunk = audio_data[:AUDIO_CHUNK_SIZE]
                audio_data = audio_data[AUDIO_CHUNK_SIZE:]

                sock.send(struct.pack(fmt, FRAME_INDICATOR, AUDIO_CHUNK_SIZE, *chunk))


def listen_for_client_audio(
    local_addr: str, local_port: int, cert_file: str, key_file: str
) -> Generator[ClientAudioPacket, None, None]:
    return retry_generator_with_backoff(
        _listen_for_client_audio, local_addr, local_port, cert_file, key_file
    )


def _listen_for_client_audio(
    local_addr: str,
    local_port: int,
    cert_file: str,
    key_file: str,
) -> Generator[ClientAudioPacket, None, None]:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unsecured_sock:
        unsecured_sock.bind((local_addr, local_port))
        unsecured_sock.listen(1)
        with context.wrap_socket(unsecured_sock, server_side=True) as sock:
            conn, sender_addr = sock.accept()
            conn.settimeout(1.5)

            while True:
                data = conn.recv(MAX_PACKET_SIZE)
                sender_addr = (sender_addr[0], local_port)

                if not data:
                    raise ConnectionError('Connection closed')

                indicator, audio_length = struct.unpack_from(HEADER_FMT, data)
                audio_fmt = f'<{audio_length}h'
                audio_bytes = bytes(
                    struct.unpack_from(audio_fmt, data, offset=HEADER_SIZE)
                )

                if indicator == FRAME_INDICATOR:
                    yield ClientAudioPacket(sender_addr, audio_bytes)
