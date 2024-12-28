import wave

import pyaudio


def main():
    fmt = pyaudio.paInt16
    rate = 44100
    channels = 1
    chunk = 1024
    record_seconds = 2
    frames = []

    audio = pyaudio.PyAudio()

    in_dev = audio.open(format=fmt, channels=channels, rate=rate, input=True, input_device_index=0, frames_per_buffer=chunk)

    print('Recording start')
    for i in range(0, int(rate / chunk * record_seconds)):
        frames.append(in_dev.read(chunk))
    print('Recording end')

    for frame in frames:
        print(frame)
    
    in_dev.stop_stream()
    in_dev.close()
    audio.terminate()

    with wave.open('testing.wav', 'wb') as f:
        f.setnchannels(channels)
        f.setsampwidth(audio.get_sample_size(fmt))
        f.setframerate(rate)
        f.writeframes(b''.join(frames))


if __name__ == '__main__':
    main()
