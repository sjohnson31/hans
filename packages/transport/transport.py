from dataclasses import dataclass
import queue
import struct
import socket
from typing import Generator, NoReturn

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2
MAX_PACKET_SIZE = 65_507
AUDIO_CHUNK_SIZE = 4096

HEADER_FMT = '<hLH'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


@dataclass
class ClientAudioPacket:
    sender_addr: tuple[str, int]
    # signed i16 pcm audio data
    audio_bytes: bytes


def stream_client_audio(
    audio_frame_q: queue.Queue[bytes], addr: str, port: str
) -> NoReturn:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    frame_num = 0
    audio_data = bytearray()
    fmt = f'{HEADER_FMT}{AUDIO_CHUNK_SIZE}h'

    while True:
        frame = audio_frame_q.get()
        audio_data.extend(frame)
        if len(audio_data) > AUDIO_CHUNK_SIZE:
            print('Got frame, sending')

            chunk = audio_data[:AUDIO_CHUNK_SIZE]
            audio_data = audio_data[AUDIO_CHUNK_SIZE:]

            server_sock.sendto(
                struct.pack(fmt, FRAME_INDICATOR, frame_num, AUDIO_CHUNK_SIZE, *chunk),
                (addr, port),
            )

            if frame_num >= MAX_COUNTER:
                frame_num = 0
            else:
                frame_num += 1


def listen_for_client_audio(
    local_addr, local_port
) -> Generator[ClientAudioPacket, None, None]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((local_addr, local_port))

    last_frame_num = None

    while True:
        data, sender_addr = sock.recvfrom(MAX_PACKET_SIZE)
        sender_addr = (sender_addr[0], local_port)

        indicator, frame_num, audio_length = struct.unpack_from(HEADER_FMT, data)
        audio_fmt = f'<{audio_length}h'
        audio_bytes = bytes(struct.unpack_from(audio_fmt, data, offset=HEADER_SIZE))

        if last_frame_num is not None:
            if frame_num != last_frame_num + 1 or (
                last_frame_num == MAX_COUNTER and frame_num != 0
            ):
                print(f'WARNING: frame {frame_num} received out of order')
                last_frame_num = frame_num
                continue

        if indicator == FRAME_INDICATOR:
            yield ClientAudioPacket(sender_addr, audio_bytes)

        last_frame_num = frame_num
