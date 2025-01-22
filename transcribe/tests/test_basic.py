from transcribe import grammar_is_valid

def test_grammar_is_valid():
    assert grammar_is_valid('root ::= "hello"')