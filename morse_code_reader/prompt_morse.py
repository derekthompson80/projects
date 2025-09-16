"""
Prompt Morse (interactive helper)

A tiny helper script that always prompts the user to enter text and prints the
Morse code output. This is a friendlier entry point for manual use than the
argparse-based CLI when you just want to type something and see the result.

Usage (from project root):
  python -m projects.morse_code_reader.prompt_morse

Or run directly:
  python projects\\morse_code_reader\\prompt_morse.py

Type an empty line or 'q' to quit.
"""
from __future__ import annotations

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


def main() -> int:
    print("Morse Code Prompt — type text to encode. Blank line or 'q' to quit.\n")
    try:
        while True:
            try:
                text = input("Enter text to encode (blank to quit): ")
            except EOFError:
                print()  # newline after Ctrl+Z/Ctrl+D
                break
            if text.strip().lower() in ("q", "quit", "exit"):
                break
            if text == "":
                break
            morse = encode_to_morse(text)
            print(f"Morse: {morse}\n")
    except KeyboardInterrupt:
        print("\nExiting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
