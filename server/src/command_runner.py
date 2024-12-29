import re
from durations_nlp import Duration
from number_parser import parse as replace_textual_numbers

# Have to replace the word "seconds", because number_parser
# will turn it into a number
SECONDS_UNITS_REPLACEMENT = '__SECONDS_UNITS__'

def run_command(command_text: str) -> bool:
    return run_timer_command(command_text)

def run_timer_command(command_text: str) -> bool:
    command_text = command_text.replace('-', ' ')
    command_text = command_text.replace('.', '')
    command_text = command_text.replace('second', SECONDS_UNITS_REPLACEMENT)
    command_text = replace_textual_numbers(command_text)
    match = re.search('\d', command_text)
    if not match:
        return False
    start, _ = match.span()
    match = re.search('time[r]?', command_text)
    if not match:
        return False
    end, _ = match.span()

    if start >=end:
        print(f'Failed {start=}, {end=}')
        return False

    duration_words = command_text[start:end].replace(SECONDS_UNITS_REPLACEMENT, 'second')
    print(f'Success {duration_words=}')
    duration = Duration(duration_words)
    print(f'Double success {duration=}')
    return True