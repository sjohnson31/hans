import pyaudio


def main():
    fmt = pyaudio.paFloat32
    rate = 44100
    chunk = 1024
    record_seconds = 2
    frames = []

    audio = pyaudio.PyAudio()

    in_dev = audio.open(format=fmt, channels=1, rate=rate, input=True, input_device_index=0, frames_per_buffer=chunk)

    print('Recording start')
    for i in range(0, int(rate / chunk * record_seconds)):
        frames.append(in_dev.read(chunk))
    print('Recording end')

    for frame in frames:
        if(frame == 0):
            print(frame)
        else:
            print('Frame is empty =(')


if __name__ == '__main__':
    main()
