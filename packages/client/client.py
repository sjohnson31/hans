from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import os
import threading
import time

import librosa
import numpy as np
from numpy.typing import NDArray
import sounddevice as sd
from transport import connect_to_server

from src.message_listener import listen


def main():
    server_ip = os.environ['SERVER_ADDRESS']
    server_port = int(os.environ['SERVER_PORT'])
    # Substring of the full device name given in sd.query_devices()
    # See https://python-sounddevice.readthedocs.io/en/0.5.1/api/streams.html#sounddevice.Stream
    # device parameter for more information
    input_device = os.environ.get('INPUT_DEVICE', sd.default.device[0])
    output_device = os.environ.get('OUTPUT_DEVICE', sd.default.device[1])

    err_q = mp.Queue()
    input_sample_rate = int(
        sd.query_devices(input_device, 'input')['default_samplerate']
    )

    with ThreadPoolExecutor() as executor:
        server_conn = connect_to_server(
            server_ip,
            server_port,
            err_q=err_q,
            executor=executor,
        )

        def input_cb(in_data: NDArray[np.float32], *_):
            new_sample = librosa.resample(
                in_data,
                orig_sr=input_sample_rate,
                target_sr=16_000,
                res_type='soxr_qq',
                axis=0,
            )
            resampled = (new_sample * np.iinfo(np.int16).max).astype(np.int16)
            server_conn.out_q.put(resampled)

        def play_cb(audio_data: NDArray[np.int16]):
            sd.play(
                audio_data,
                # This is the samplerate coming out of the TTS
                # TODO: Encode samplerate in transport packet
                samplerate=48_000,
                device=output_device,
                blocking=True,
            )

        listener_thread = threading.Thread(
            target=listen,
            args=[play_cb, server_conn.in_q],
            name='listener_thread',
            daemon=True,
        )
        listener_thread.start()

        with sd.InputStream(
            device=input_device,
            channels=1,
            callback=input_cb,
            samplerate=input_sample_rate,
        ):
            while True:
                time.sleep(1000)


if __name__ == '__main__':
    main()
