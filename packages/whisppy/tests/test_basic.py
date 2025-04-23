from os.path import dirname
import wave
from pathlib import Path

import pytest
import numpy as np
from numpy.typing import NDArray

from whisppy import grammar_parse, transcriber


@pytest.fixture
def resource_path():
    return Path(dirname(__file__)).joinpath("../../../resources").resolve()


@pytest.fixture
def model(resource_path: Path):
    return resource_path.joinpath("models", "ggml-tiny.en.bin")


@pytest.fixture
def five_minute_timer_samples(resource_path: Path):
    with open(resource_path.joinpath("samples", "5min_timer.wav"), "rb") as wav_file:
        wav_data = samples(wav_file)
    return wav_data


@pytest.fixture
def jibberish_samples(resource_path: Path):
    with open(resource_path.joinpath("samples", "jibberish.wav"), "rb") as wav_file:
        wav_data = samples(wav_file)
    return wav_data


def samples(wav_file: Path) -> NDArray[np.float16]:
    with wave.open(wav_file, "rb") as wav:
        raw_data = wav.readframes(wav.getnframes())
        sample_data = np.frombuffer(raw_data, dtype=np.int16)
        sample_data = sample_data.astype(np.float32) / np.iinfo(np.int16).max
    return sample_data


def test_grammar_parse():
    assert grammar_parse('root ::= "hello"') is not None


def test_transcribe(model: Path, five_minute_timer_samples):
    with transcriber(
        str(model), gbnf_grammar='root ::= "Hey Hans, set a timer for 5 minutes"'
    ) as t:
        text = t.transcribe(
            five_minute_timer_samples,
            initial_prompt="Hey Hans, set a timer for 5 minutes",
            grammar_rule="root",
        )
        assert text == "Hey Hans, set a timer for 5 minutes"


def test_transcribe_non_grammar_sentence(model: Path, jibberish_samples):
    with transcriber(
        str(model), gbnf_grammar='root ::= "Hey Hans, set a timer for 5 minutes"'
    ) as t:
        text = t.transcribe(
            jibberish_samples,
            initial_prompt="Hey Hans, set a timer for 5 minutes",
            grammar_rule="root",
        )
        assert text == ""
