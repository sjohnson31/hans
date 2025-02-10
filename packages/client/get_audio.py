import os
import queue
import threading
import time

import pyaudio
import librosa
import numpy as np
from transport import stream_client_audio

from src.message_listener import listen

def main():
    fmt = pyaudio.paInt16
    channels = 1
    chunk = 1024
    frame_q = queue.Queue()
    server_ip = os.environ['SERVER_ADDRESS']
    server_port = int(os.environ['SERVER_PORT'])
    client_port = int(os.environ['CLIENT_PORT'])
    input_device_index = int(os.environ['INPUT_DEVICE_INDEX'])
    output_device_index = int(os.environ['OUTPUT_DEVICE_INDEX'])
    process_thread = threading.Thread(target=stream_client_audio, args=(frame_q, server_ip, server_port), daemon=True)
    process_thread.start()

    audio = pyaudio.PyAudio()
    input_device_info = audio.get_device_info_by_index(input_device_index)
    rate_input = int(input_device_info.get('defaultSampleRate'))
    if not rate_input:
        sys.exit('Critical: selected input device does not have a sample rate. Exiting')
    output_device_info = audio.get_device_info_by_index(output_device_index)
    # While getting the input rate is crucial (on Linux, Windows doesn't seem to care),
    # getting a device's actual output rate doesn't seem to matter so much
    rate_output = int(output_device_info.get('defaultSampleRate', 44100))
    # for i in range(audio.get_device_count()):
    #    print(audio.get_device_info_by_index(i))

    def input_cb(in_data, frame_count: int, time_info, status_flags):
        out_data = None
        flag = pyaudio.paContinue
        new_sample = librosa.resample(np.frombuffer(in_data, np.int16).astype(np.float32), orig_sr=rate_input, target_sr=16000)
        frame_q.put(new_sample.astype(np.int16).tobytes())
        return (out_data, flag)

    def play_cb(audio_data):
        start_i = 0
        def inner_cb(_, frame_count: int, time_info, status_flags):
            nonlocal start_i
            print(f'{frame_count=}, {start_i=}')
            data_to_send = audio_data[start_i:start_i + (frame_count * 2)]
            start_i += frame_count * 2
            return(data_to_send, pyaudio.paContinue)
        
        stream = audio.open(format=audio.get_format_from_width(2), channels=1, rate=rate_output, output=True, output_device_index=output_device_index, stream_callback=inner_cb)
        while stream.is_active():
            time.sleep(0.1)
        stream.close()
    
    listener_thread = threading.Thread(target=listen, args=[play_cb, client_port], daemon=True)
    listener_thread.start()

    try:
        in_dev = audio.open(format=fmt, channels=channels, rate=rate_input, input=True, input_device_index=input_device_index, frames_per_buffer=chunk, stream_callback=input_cb)
        while process_thread.is_alive():
            process_thread.join(0.5)
    finally:
        in_dev.stop_stream()
        in_dev.close()
        audio.terminate()


if __name__ == '__main__':
    main()
