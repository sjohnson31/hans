from __future__ import annotations

from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import multiprocessing as mp
from os.path import dirname
from pathlib import Path
import queue
import socket
import ssl
from tempfile import NamedTemporaryFile
import threading
import time

import pytest
from transport import connect_to_server, listen_for_clients


@pytest.fixture
def resource_path():
    return Path(dirname(__file__)).joinpath('../../resources').resolve()


@pytest.fixture(scope='module')
def unused_port() -> int:
    sock = socket.socket()
    sock.bind(('', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@dataclass
class SSLKeyPair:
    cert_file: NamedTemporaryFile
    key_file: NamedTemporaryFile


@pytest.fixture(scope='module')
def ssl_key_pair() -> Generator[SSLKeyPair]:
    cert_dir = Path(dirname(__file__)).joinpath('../../certs').resolve()
    return SSLKeyPair(
        cert_file=cert_dir.joinpath('hans.local.pem'),
        key_file=cert_dir.joinpath('hans.local-key.pem'),
    )


def test_transport(unused_port, ssl_key_pair):
    print(unused_port)
    err_q = mp.Queue()
    received_msg_q = mp.Queue()

    def enqueuing_conn_handler(
        in_q: mp.Queue[bytes], out_q: mp.Queue[bytes], stop_event: threading.Event
    ):
        while not stop_event.is_set():
            try:
                received_msg_q.put(in_q.get_nowait())
            except queue.Empty:
                time.sleep(0.001)

    with ThreadPoolExecutor() as executor:
        print('Starting executor')
        executor.submit(
            listen_for_clients,
            local_addr='hans.local',
            local_port=unused_port,
            cert_file=ssl_key_pair.cert_file,
            key_file=ssl_key_pair.key_file,
            conn_cb=enqueuing_conn_handler,
            err_q=err_q,
            executor=executor,
        )

        context = ssl.create_default_context()
        client_conn = connect_to_server(
            server_addr='hans.local',
            server_port=unused_port,
            err_q=err_q,
            executor=executor,
            context=context,
        )

        client_conn.out_q.put(b'This is a test')
        assert received_msg_q.get() == b'This is a test'
