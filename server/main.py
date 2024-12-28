from pywhispercpp.model import Model


def main():
    model = Model('base.en')
    segments = model.transcribe('../whisper.cpp/5_second_timer.wav')
    for i, segment in enumerate(segments):
        print(f'{i}: {segment.text}')


if __name__ == '__main__':
    main()
