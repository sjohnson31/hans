from transcribe import hello, hello_two, grammar_is_valid

def test_hello():
    assert hello() == "Hello from transcribe!"

def test_hello_two():
    assert hello_two() == "Hello from transcribe two!"

def test_grammar_is_valid():
    assert grammar_is_valid('root ::= "hello"')