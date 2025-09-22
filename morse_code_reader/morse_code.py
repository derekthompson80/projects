"""
Morse Code encoder module with a simple interactive CLI.

Exports:
- encode_to_morse(text, unknown='?') -> str

When run as a script it prompts the user for input and prints the
encoded Morse output. Words are separated with " / " and letters with
single spaces. Unknown characters are replaced by the unknown token
(default "?"). Whitespace is normalized.
"""
from __future__ import annotations

from typing import Dict

# ITU Morse mapping for letters, digits, and common punctuation
MORSE_CODE: Dict[str, str] = {
    'A': '.-',   'B': '-...', 'C': '-.-.', 'D': '-..',  'E': '.',
    'F': '..-.', 'G': '--.',  'H': '....', 'I': '..',   'J': '.---',
    'K': '-.-',  'L': '.-..', 'M': '--',   'N': '-.',   'O': '---',
    'P': '.--.', 'Q': '--.-', 'R': '.-.',  'S': '...',  'T': '-',
    'U': '..-',  'V': '...-', 'W': '.--',  'X': '-..-', 'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
    '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.', '!': '-.-.--',
    '/': '-..-.',  '(': '-.--.',  ')': '-.--.-', '&': '.-...',  ':': '---...',
    ';': '-.-.-.', '=': '-...-',  '+': '.-.-.',  '-': '-....-', '_': '..--.-',
    '"': '.-..-.', '$': '...-..-', '@': '.--.-.',
}


def encode_to_morse(text: str, unknown: str = '?') -> str:
    """Encode arbitrary text into Morse code.

    - Collapses and normalizes whitespace between words.
    - Uses a single space between encoded letters and " / " between words.
    - Replaces unmapped characters with the provided unknown token.
    """
    if not text:
        return ''

    words = str(text).split()
    encoded_words: list[str] = []

    for word in words:
        letters: list[str] = []
        for ch in word:
            code = MORSE_CODE.get(ch.upper())
            letters.append(code if code is not None else unknown)
        encoded_words.append(' '.join(letters))

    return ' / '.join(encoded_words)


def main() -> int:
    try:
        text = input('Enter text: ')
    except EOFError:
        return 0
    print(encode_to_morse(text))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())