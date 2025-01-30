from contextlib import contextmanager
from typing import Generator

import numpy as np
from numpy.typing import NDArray

import transcribe._core as _c

grammar_parse = _c.grammar_parse

class Transcriber:
    def __init__(self, ctx: _c.WhisperContext):
        self._ctx = ctx

    def transcribe(self, samples: NDArray[np.float32], initial_prompt: str, gbnf_grammar: str, grammar_rule: str) -> str:
        return _c.transcribe(self._ctx, samples, initial_prompt, gbnf_grammar, grammar_rule)


@contextmanager
def transcriber(model_path: str) -> Generator[Transcriber]:
    try:
        ctx = _c.context_init(model_path)
        yield Transcriber(ctx)
    finally:
        if (ctx):
            _c.context_free(ctx)
