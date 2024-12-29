import os
import socket
from typing import NoReturn

MAX_PACKET_SIZE = 65_507


def listen() -> NoReturn:
    udp_ip = '0.0.0.0'
    udp_port = int(os.environ['SERVER_PORT'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))

    while True:
        message, _ = sock.recvfrom(MAX_PACKET_SIZE)
        print(f'Got message {message.decode()}')
