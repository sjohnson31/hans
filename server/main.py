import socket
import struct

from pywhispercpp.model import Model


def main():
    udp_ip = '0.0.0.0'
    udp_port = 8888
    # TODO: Are frames always this big?
    frame_len = 2048
    packet_fmt = f'<L{frame_len}h'
    packet_size = struct.calcsize(packet_fmt)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))

    #model = Model('base.en')
    #segments = model.transcribe('../whisper.cpp/5_second_timer.wav')
    #for i, segment in enumerate(segments):
    #    print(f'{i}: {segment.text}')
    while True:
        data, addr = sock.recvfrom(packet_size)
        frame_num, *frame = struct.unpack(packet_fmt, data)
        print(f'Received frame: {frame_num}')


if __name__ == '__main__':
    main()
