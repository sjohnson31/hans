import socket
import struct
import sys
import wave

import numpy as np

from pywhispercpp.model import Model

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2


def write_audio(frames):
    channels = 1
    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(frames)
        

def main():
    udp_ip = '0.0.0.0'
    udp_port = 8888
    # TODO: Are frames always this big?
    frame_len = 2048
    packet_fmt = f'<hL{frame_len}h'
    packet_size = struct.calcsize(packet_fmt)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))

    frames = []
    model = Model('base.en')
    #segments = model.transcribe('../whisper.cpp/5_second_timer.wav')
    #for i, segment in enumerate(segments):
    #    print(f'{i}: {segment.text}')
    last_frame_num = None
    while True:
        data, _ = sock.recvfrom(packet_size)
        indicator, frame_num, *frame = struct.unpack(packet_fmt, data)
        print(f'Received frame: {frame_num}')
        if last_frame_num is not None:
            if frame_num != last_frame_num + 1 or (last_frame_num == MAX_COUNTER and frame_num != 0):
                print('WARNING: Received frames out of order')
        if indicator == FRAME_INDICATOR:
            frames.append(bytes(frame))
        elif indicator == END_INDICATOR:
            print('End indicator recieved')
            #segments = model.transcribe(np.frombuffer(b''.join(frames), np.int16))
            write_audio(np.frombuffer(b''.join(frames), np.int16).tobytes())
            segments = model.transcribe('testing.wav')
            for segment in segments:
                print(segment.text)
            sys.exit(0)
            frames = np.array([])
        last_frame_num = frame_num



if __name__ == '__main__':
    main()
