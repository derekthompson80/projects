def reverse_words(text):
    """
    Reverses each word in the input string while preserving all spaces.
    
    Args:
        text (str): The input string to process
        
    Returns:
        str: A new string with each word reversed but spaces preserved
        
    Examples:
        >>> reverse_words("Hello World")
        'olleH dlroW'
        >>> reverse_words("Hello  World")
        'olleH  dlroW'
        >>> reverse_words("  Hello World  ")
        '  olleH dlroW  '
        >>> reverse_words("")
        ''
    """
    if not text:
        return ""
    
    result = []
    current_word = ""
    spaces = ""
    
    for char in text:
        if char == " ":
            # If we have a word collected, add it reversed to the result
            if current_word:
                result.append(current_word[::-1])
                current_word = ""
            # Collect spaces
            spaces += " "
        else:
            # If we have spaces collected, add them to the result
            if spaces:
                result.append(spaces)
                spaces = ""
            # Collect characters for the current word
            current_word += char
    
    # Handle any remaining word or spaces
    if current_word:
        result.append(current_word[::-1])
    if spaces:
        result.append(spaces)
    
    return "".join(result)


# Test cases
if __name__ == "__main__":
    test_cases = [
        "Hello World",
        "Hello  World",
        "  Hello World  ",
        "Python is awesome",
        "",
        "SingleWord",
        "   ",
        "a b c d e f"
    ]
    
    # Expected outputs for verification
    expected_outputs = [
        "olleH dlroW",
        "olleH  dlroW",
        "  olleH dlroW  ",
        "nohtyP si emosewa",
        "",
        "droWelgniS",
        "   ",
        "a b c d e f"
    ]
    
    for i, test in enumerate(test_cases):
        result = reverse_words(test)
        expected = expected_outputs[i]
        print(f"Input: '{test}'")
        print(f"Output: '{result}'")
        print(f"Expected: '{expected}'")
        print(f"Test passed: {result == expected}")
        print("-" * 30)