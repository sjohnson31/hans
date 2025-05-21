from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import Executor
from dataclasses import dataclass
import multiprocessing as mp
import socket
import ssl
import struct
import threading
import traceback
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from src.retry import retry_generator_with_backoff, retry_with_backoff

FRAME_INDICATOR = 1
MAX_FRAME_SIZE = 4_294_967_295

# Stop Indicator, then audio length
HEADER_FMT = '<hL'
HEADER_SIZE = struct.calcsize(HEADER_FMT)


@dataclass
class ClientAudioPacket:
    sender_addr: tuple[str, int]
    # signed i16 pcm audio data
    audio_bytes: bytes


class ConnectionHandler(Protocol):
    def __call__(
        self,
        in_q: mp.Queue[NDArray[np.int16]],
        out_q: mp.Queue[NDArray[np.int16]],
        err_q: mp.Queue[Exception],
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
        raise e

    print('loaded cert chain')
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unsecured_sock,
    ):
        futures = []
        print('binding', local_addr, local_port)
        unsecured_sock.bind((local_addr, local_port))
        unsecured_sock.listen()
        with context.wrap_socket(unsecured_sock, server_side=True) as sock:
            sock.settimeout(5)
            sock.listen()
            while err_q.empty():
                try:
                    conn, _ = sock.accept()
                except TimeoutError:
                    continue
                print('got past accept')
                try:
                    t = threading.Thread(
                        target=handle_connection,
                        args=[conn, conn_cb, err_q],
                        daemon=True,
                    )
                    t.start()
                    futures.append(t)
                except:
                    traceback.print_exc()
                    raise


@dataclass
class ServerConnection:
    in_q: mp.Queue[NDArray[np.int16]]
    out_q: mp.Queue[NDArray[np.int16]]


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


def ferry_audio(
    conn,
    in_q: mp.Queue[NDArray[np.int16]],
    out_q: mp.Queue[NDArray[np.int16]],
    err_q: mp.Queue,
) -> None:
    conn.setblocking(False)
    bytes_to_send = bytearray()
    received_bytes = bytearray()
    while True:
        #out_selections = [conn] if bytes_to_send else []
        #(read_ready, write_ready, []) = select.select(
            #[conn, out_q._reader, err_q._reader], out_selections, []
        #)
        selections = [conn, out_q._reader, err_q._reader]
        ready = mp.connection.wait(selections)
        if err_q._reader in ready:
            return
        if conn in ready:
            try:
                data = conn.recv()
            except TimeoutError:
                pass
            except:
                # This is to skip an SSL error which seems to just happen once
                # TODO: fix source of error and remove this
                traceback.print_exc()
                continue
            else:
                if not data:
                    raise RuntimeError('Connection dropped')

                received_bytes.extend(data)

                if len(received_bytes) > 2:
                    indicator, num_shorts_audio = struct.unpack_from(
                        HEADER_FMT, received_bytes
                    )
                    if indicator != FRAME_INDICATOR:
                        raise RuntimeError('Got invalid packet')

                    if len(received_bytes) - HEADER_SIZE >= num_shorts_audio * 2:
                        # We have a whole packet, process it
                        audio_segment = received_bytes[
                            HEADER_SIZE : HEADER_SIZE + num_shorts_audio * 2
                        ]
                        audio = np.frombuffer(audio_segment, dtype=np.int16)
                        in_q.put_nowait(audio)
                        received_bytes = received_bytes[HEADER_SIZE + len(audio_segment) :]

        if out_q._reader in ready:
            # This should not throw because we were just woken up to handle
            # something being put on the queue
            data = out_q.get_nowait()
            num_shorts = len(data)
            data_bytes = data.tobytes()
            assert len(data_bytes) % 2 == 0, (
                'Length of audio data must be divisible by 2'
            )
            if (num_shorts * 2) > MAX_FRAME_SIZE:
                raise RuntimeError(
                    f'Audio data too large: {num_shorts * 2} > {MAX_FRAME_SIZE}'
                )
            bytes_to_send.extend(struct.pack(HEADER_FMT, FRAME_INDICATOR, num_shorts))
            bytes_to_send.extend(data_bytes)
        if bytes_to_send and conn in ready:
            try:
                bytes_sent = conn.send(bytes_to_send)
            except TimeoutError:
                pass
            else: 
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
                data = conn.recv(MAX_FRAME_SIZE)
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
