from transcribe._core import hello_from_bin
from transcribe._core import hello_from_bin_two
from transcribe._core import verify_grammar

def hello() -> str:
    return hello_from_bin()

def hello_two() -> str:
    return hello_from_bin_two()

def grammar_is_valid(grammar: str) -> bool:
    return verify_grammar(grammar) == 0
