from transcribe._core import verify_grammar


def grammar_is_valid(grammar: str) -> bool:
    return verify_grammar(grammar) == 0
