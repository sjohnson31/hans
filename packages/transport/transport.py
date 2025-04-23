from __future__ import annotations

from collections.abc import Callable, Generator
from concurrent.futures import Executor
from dataclasses import dataclass
import multiprocessing as mp
import numpy as np
from numpy.typing import NDArray
import queue
import select
import socket
import ssl
import struct
import threading
import traceback
from typing import NoReturn, Protocol

from src.retry import retry_generator_with_backoff, retry_with_backoff

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2
MAX_PACKET_SIZE = 65_507
AUDIO_CHUNK_SIZE = 4096

# Stop Indicator, then audio length
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


class ConnectionHandler(Protocol):
    def __call__(
        self, in_q: mp.Queue[bytes], out_q: mp.Queue[bytes], stop_event: threading.Event
    ):
        pass


def listen_for_clients(
    local_addr: str,
    local_port: str,
    cert_file: str,
    key_file: str,
    conn_cb: ConnectionHandler,
    executor: Executor,
    err_q: mp.Queue,
):
    print('started listening')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(cert_file, key_file)
    except BaseException as e:
        print(cert_file)
        print(key_file)
        print(e)

    print('loaded cert chain')
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unsecured_sock,
    ):
        futures = []
        print('binding', local_addr, local_port)
        unsecured_sock.bind((local_addr, local_port))
        unsecured_sock.listen()
        with context.wrap_socket(unsecured_sock, server_side=True) as sock:
            sock.settimeout(15)
            sock.listen()
            while err_q.empty():
                try:
                    conn, _ = sock.accept()
                except TimeoutError:
                    continue
                print('got past accept')
                try:
                    #futures.append(executor.submit(handle_connection, args=[conn, conn_cb, err_q]))
                    t = threading.Thread(target=handle_connection, args=[conn, conn_cb, err_q], daemon=True)
                    t.start()
                    futures.append(t)
                    print('Task submitted, boss')
                except:
                    traceback.print_exc()
                    raise


@dataclass
class ServerConnection:
    in_q: mp.Queue
    out_q: mp.Queue[bytes]


def connect_to_server(
    server_addr: str,
    server_port: int,
    err_q: mp.Queue,
    executor: Executor,
    context: ssl.SSLContext = None,
) -> ServerConnection:
    print('Begin connect to server')
    if context is None:
        context = ssl.create_default_context()

    def connect_with_retries():
        print('Begin connect with retries')
        try:
            retry_with_backoff(
                retry_err_q=err_q,
                func=_connect_to_server_once,
                server_addr=server_addr,
                server_port=server_port,
                in_q=in_q,
                out_q=out_q,
                err_q=err_q,
                context=context,
            )
        except BaseException as e:
            print(e)

    in_q: mp.Queue[bytes] = mp.Queue()
    out_q: mp.Queue[bytes] = mp.Queue()
    executor.submit(connect_with_retries)
    return ServerConnection(in_q, out_q)


def _connect_to_server_once(
    server_addr,
    server_port,
    in_q,
    out_q,
    err_q: mp.Queue,
    context: ssl.SSLContext,
):
    with (
        socket.create_connection(
            (server_addr, server_port), timeout=1.5
        ) as unsecured_sock,
        context.wrap_socket(unsecured_sock, server_hostname=server_addr) as sock,
    ):
        ferry_audio(sock, in_q, out_q, err_q)


def ferry_audio(conn, in_q: mp.Queue[NDArray[np.int16]], out_q: mp.Queue[NDArray[np.int16]], err_q: mp.Queue) -> None:
    conn.setblocking(False)
    bytes_to_send = bytearray()
    received_bytes = bytearray()
    while True:
        out_selections = [conn] if bytes_to_send else []
        print('starting select')
        (read_ready, write_ready, []) = select.select(
            [conn, out_q._reader, err_q._reader], out_selections, []
        )
        print(f'{read_ready=}')
        print('got out of select')
        if err_q._reader in read_ready:
            return
        if conn in read_ready:
            try:
                data = conn.recv()
            except:
                traceback.print_exc()
                continue

            if not data:
                raise RuntimeError('Connection dropped')

            received_bytes.extend(data)

            if len(received_bytes) > 2:
                indicator, num_shorts_audio = struct.unpack_from(HEADER_FMT, received_bytes)
                print(f'{num_shorts_audio=}')
                if indicator != FRAME_INDICATOR:
                    raise RuntimeError('Got invalid packet')

                if len(received_bytes) - HEADER_SIZE >= num_shorts_audio * 2:
                    # We have a whole packet, process it
                    audio = np.frombuffer(data, dtype=np.int16, offset=HEADER_SIZE)
                    print('audio received')
                    in_q.put_nowait(audio)
                    received_bytes = received_bytes[HEADER_SIZE + len(audio) :]

        if out_q._reader in read_ready:
            # This should not throw because we were just woken up to handle
            # something being put on the queue
            data = out_q.get_nowait()
            num_shorts = len(data)
            data_bytes = data.tobytes()
            assert len(data_bytes) % 2 == 0, 'Length of audio data must be divisible by 2'
            bytes_to_send.extend(struct.pack(HEADER_FMT, FRAME_INDICATOR, num_shorts))
            bytes_to_send.extend(data_bytes)
        if conn in write_ready or bytes_to_send:
            bytes_sent = conn.send(bytes_to_send)
            bytes_to_send = bytes_to_send[bytes_sent:]


def handle_connection(
    conn: socket.socket,
    conn_handler_cb: ConnectionHandler,
    err_q: mp.Queue[Exception],
    timeout_secs=5,
):
    in_q: mp.Queue[bytes] = mp.Queue()
    out_q: mp.Queue[bytes] = mp.Queue()
    stop_event = threading.Event()
    t = threading.Thread(
        target=conn_handler_cb, args=[in_q, out_q, stop_event], daemon=True
    )
    t.start()
    print('Thread started')
    try:
        ferry_audio(conn=conn, in_q=in_q, out_q=out_q, err_q=err_q)
    except:
        traceback.print_exc()
        raise
    finally:
        # TODO: Logs???
        print('Exiting handle_connection')
        stop_event.set()
        t.join(timeout_secs)


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
