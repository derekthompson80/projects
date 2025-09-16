"""
Usability Test for Morse Code Converter

This script runs a few representative test cases against the simple
`encode_to_morse` function and prints a readable report. It also offers an
optional interactive prompt at the end for manual trials.

Run from project root:
  python -m projects.morse_code_reader.usability_test

Or run directly:
  python projects\\morse_code_reader\\usability_test.py

Options:
  --no-interactive   Skip the interactive prompt at the end.
"""
from __future__ import annotations

import argparse

# Support both package and script execution
try:
    from .morse_code import encode_to_morse  # type: ignore
except Exception:
    # Fallback for running this file directly
    import os, sys
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    if CURRENT_DIR not in sys.path:
        sys.path.insert(0, CURRENT_DIR)
    from morse_code import encode_to_morse


def run_tests() -> tuple[int, int]:
    """Run a handful of sample tests. Returns (passed, total)."""
    cases = [
        ("HELLO WORLD", ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."),
        ("SOS!", "... --- ... -.-.--"),
        ("Hi\tthere", ".... .. / - .... . .-. ."),  # whitespace normalization
        ("", ""),
        ("Hi 🙂", ".... .. / ?"),  # unknown char becomes '?'
    ]

    passed = 0
    for i, (text, expected) in enumerate(cases, 1):
        got = encode_to_morse(text)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] Case {i}: {text!r}")
        print(f"  Expected: {expected}")
        print(f"  Got     : {got}\n")
        if ok:
            passed += 1
    total = len(cases)
    print(f"Summary: {passed}/{total} tests passed\n")
    return passed, total


def interactive_prompt() -> None:
    print("Interactive trial — type text to encode. Blank line to finish.\n")
    try:
        while True:
            try:
                text = input("Enter text: ")
            except EOFError:
                print()
                break
            if text == "":
                break
            print(f"Morse: {encode_to_morse(text)}\n")
    except KeyboardInterrupt:
        print("\nExiting interactive mode.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Usability test runner for Morse encoder")
    parser.add_argument("--no-interactive", action="store_true", help="Skip interactive prompt")
    args = parser.parse_args()

    run_tests()
    if not args.no_interactive:
        interactive_prompt()
