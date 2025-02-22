import os
import queue
import threading

import librosa
import numpy as np
from numpy.typing import NDArray
import sounddevice as sd
from transport import stream_client_audio
from audio_debugger import AudioDebugger

from src.message_listener import listen


def main():
    frame_q = queue.Queue()
    server_ip = os.environ['SERVER_ADDRESS']
    server_port = int(os.environ['SERVER_PORT'])
    client_port = int(os.environ['CLIENT_PORT'])
    # Substring of the full device name given in sd.query_devices()
    # See https://python-sounddevice.readthedocs.io/en/0.5.1/api/streams.html#sounddevice.Stream
    # device parameter for more information
    input_device = os.environ.get('INPUT_DEVICE', 'default')
    output_device = os.environ.get('OUTPUT_DEVICE', 'default')

    process_thread = threading.Thread(
        target=stream_client_audio, args=(frame_q, server_ip, server_port), daemon=True
    )
    process_thread.start()
    input_sample_rate = int(
        sd.query_devices(input_device, 'input')['default_samplerate']
    )
    input_sample_rate = 16_000

    dbg = AudioDebugger(sample_rate=input_sample_rate)

    def input_cb(in_data: NDArray[np.int16], *_):
        dbg.append(in_data)
        new_sample = librosa.resample(
            in_data.astype(np.float32),
            orig_sr=input_sample_rate,
            target_sr=16000,
        )
        frame_q.put(new_sample.astype(np.int16).tobytes())

    def play_cb(audio_data: bytearray):
        sd.play(
            np.frombuffer(audio_data, np.int16),
            samplerate=16000,
            device=output_device,
            blocking=True,
        )

    listener_thread = threading.Thread(
        target=listen, args=[play_cb, client_port], daemon=True
    )
    listener_thread.start()

    with sd.InputStream(
        device=input_device,
        callback=input_cb,
        blocksize=1024,
        samplerate=input_sample_rate,
    ):
        while process_thread.is_alive():
            process_thread.join(0.5)


if __name__ == '__main__':
    main()
