import os
import queue
import socket
import threading
import time

import pyaudio

from src.process_input import send_audio_frames
import librosa
import numpy as np


def main():
    fmt = pyaudio.paInt16
    rate = 48000
    #rate = 44100 # native sampling rate of audio devices
    channels = 1
    chunk = 1024
    frame_q = queue.Queue()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_ip = os.environ['SERVER_ADDRESS']
    server_port = int(os.environ['SERVER_PORT'])
    input_device_index = int(os.environ['INPUT_DEVICE_INDEX'])
    trigger_transcription_event = threading.Event()
    process_thread = threading.Thread(target=send_audio_frames, args=(frame_q, server_sock, server_ip, server_port, trigger_transcription_event), daemon=True)
    process_thread.start()

    audio = pyaudio.PyAudio()
    # for i in range(audio.get_device_count()):
    #     print(audio.get_device_info_by_index(i))

    def stream_cb(in_data, frame_count: int, time_info, status_flags):
        out_data = None
        flag = pyaudio.paContinue
        #print(len(in_data))
        new_sample = librosa.resample(np.frombuffer(in_data, np.int16).astype(np.float32), orig_sr=rate, target_sr=16000)
        frame_q.put(new_sample.astype(np.int16).tobytes())
        return (out_data, flag)

    try:
        in_dev = audio.open(format=fmt, channels=channels, rate=rate, input=True, input_device_index=input_device_index, frames_per_buffer=chunk, stream_callback=stream_cb)
        start_time = time.monotonic()
        while process_thread.is_alive():
            process_thread.join(0.5)
            if time.monotonic() - start_time > 5:
                trigger_transcription_event.set()
                start_time = time.monotonic()
    finally:
        in_dev.stop_stream()
        in_dev.close()
        audio.terminate()

        #with wave.open('testing.wav', 'wb') as f:
            #f.setnchannels(channels)
            #f.setsampwidth(audio.get_sample_size(fmt))
            #f.setframerate(rate)
            #f.writeframes(b''.join(frames))

    #print('Recording start')
    #for i in range(0, int(rate / chunk * record_seconds)):
        #frames.append(in_dev.read(chunk))
    #print('Recording end')



if __name__ == '__main__':
    main()
