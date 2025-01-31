from importlib import resources
import wave
import os
from pathlib import Path

import pytest
import numpy as np
from numpy.typing import NDArray

from whisppy import grammar_parse, transcriber


@pytest.fixture
def files():
    return resources.files()

@pytest.fixture
def model(files):
    with resources.as_file(files.joinpath('models', 'ggml-tiny.en.bin')) as model_file:
        yield model_file

@pytest.fixture
def five_minute_timer_samples(files):
    with resources.as_file(files.joinpath('samples', '5min_timer.wav')) as wav_file:
        yield samples(wav_file)

def samples(wav_file: os.PathLike) -> NDArray[np.float16]:
    with wave.open(str(wav_file), 'rb') as wav:
        raw_data = wav.readframes(wav.getnframes())
        sample_data = np.frombuffer(raw_data, dtype=np.int16)
        sample_data = sample_data.astype(np.float32) / np.iinfo(np.int16).max
    return sample_data


def test_grammar_parse():
    assert grammar_parse('root ::= "hello"') is not None

def test_transcribe(model: Path, five_minute_timer_samples):
    with transcriber(str(model), gbnf_grammar='root ::= "Hey Hans, set a timer for 5 minutes"') as t:
        text = t.transcribe(
            five_minute_timer_samples,
            initial_prompt="Hey Hans, set a timer for 5 minutes",
            grammar_rule="root",
        )
        assert text == "Hey Hans, set a timer for 5 minutes"
