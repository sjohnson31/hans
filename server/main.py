import os
import socket
import struct
import sys
import wave

import numpy as np

from pywhispercpp.model import Model

MAX_COUNTER = 4_294_967_295
FRAME_INDICATOR = 1
END_INDICATOR = 2
MAX_PACKET_SIZE = 65_507


def write_audio(frames):
    channels = 1
    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(frames)
        

def main():
    udp_ip = '0.0.0.0'
    udp_port = int(os.environ['SERVER_PORT'])
    header_fmt = '<hLH'
    header_size = struct.calcsize(header_fmt)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))

    frames = []
    model = Model('base.en')
    #segments = model.transcribe('../whisper.cpp/5_second_timer.wav')
    #for i, segment in enumerate(segments):
    #    print(f'{i}: {segment.text}')
    last_frame_num = None
    while True:
        data, _ = sock.recvfrom(MAX_PACKET_SIZE)
        indicator, frame_num, audio_length = struct.unpack_from(header_fmt, data)
        audio_fmt = f'<{audio_length}h'
        print(f'indicator={indicator}, frame_num={frame_num}, audio_length={audio_length}, len={len(data)}')
        audio_bytes = bytes(struct.unpack_from(audio_fmt, data, offset=header_size))

        if last_frame_num is not None:
            if frame_num != last_frame_num + 1 or (last_frame_num == MAX_COUNTER and frame_num != 0):
                print('WARNING: Received frames out of order')
        if indicator == FRAME_INDICATOR:
            frames.append(audio_bytes)
        elif indicator == END_INDICATOR:
            print('End indicator recieved')
            #segments = model.transcribe(np.frombuffer(b''.join(frames), np.int16))
            write_audio(b''.join(frames))
            segments = model.transcribe('testing.wav')
            for segment in segments:
                print(segment.text)
            sys.exit(0)
            frames = np.array([])
        last_frame_num = frame_num



if __name__ == '__main__':
    main()
