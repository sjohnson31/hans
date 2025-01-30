from contextlib import contextmanager
from typing import Generator

import numpy as np
from numpy.typing import NDArray

import whisppy._whisppy as _w

WhisperContext = _w.WhisperContext
ParsedGrammar = _w.ParsedGrammar
grammar_parse = _w.grammar_parse

class Transcriber:
    def __init__(self, ctx: WhisperContext, grammar: ParsedGrammar):
        self._ctx = ctx
        self._grammar = grammar

    def transcribe(self, samples: NDArray[np.float32], initial_prompt: str, grammar_rule: str) -> str:
        return _w.transcribe(self._ctx, samples, initial_prompt, self._grammar, grammar_rule)


@contextmanager
def transcriber(model_path: str, gbnf_grammar: str) -> Generator[Transcriber]:
    try:
        ctx = _w.context_init(model_path)
        grammar = _w.grammar_parse(gbnf_grammar)
        yield Transcriber(ctx, grammar)
    finally:
        if (ctx):
            _w.context_free(ctx)
