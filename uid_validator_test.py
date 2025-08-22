from uid_validator import is_valid_uid

# Test cases
test_cases = [
    # Valid UIDs
    ("B1CD102354", True),  # 2 uppercase, 6 digits, 10 chars, no repeats
    ("AB1234567C", True),  # 3 uppercase, 7 digits, 10 chars, no repeats
    ("1A2B3C4D5E", True),  # 5 uppercase, 5 digits, 10 chars, no repeats
    
    # Invalid UIDs
    ("1a2b3c4d5e", False),  # No uppercase letters
    ("A1B2C3D4E5", False),  # Only 1 uppercase letter
    ("ABCDEFGHIJ", False),  # No digits
    ("AB12CD34EF", False),  # Only 2 digits
    ("AB12345678", False),  # Only 2 uppercase letters, but valid
    ("AB123456789", False),  # 11 characters (too long)
    ("AB12345", False),     # 7 characters (too short)
    ("AA12345678", False),  # Repeated character 'A'
    ("A!1234567B", False),  # Contains non-alphanumeric character '!'
]

# Run tests
passed = 0
failed = 0

for uid, expected in test_cases:
    result = is_valid_uid(uid)
    if result == expected:
        status = "PASS"
        passed += 1
    else:
        status = "FAIL"
        failed += 1
    
    print(f"{status}: UID='{uid}', Expected={expected}, Got={result}")

print(f"\nTest Summary: {passed} passed, {failed} failed")