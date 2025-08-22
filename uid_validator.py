def is_valid_uid(uid):
    """
    Validates a UID according to the following rules:
    1. Contains at least 2 uppercase English alphabet characters
    2. Contains at least 3 digits (0-9)
    3. Contains only alphanumeric characters
    4. No character repeats
    5. Exactly 10 characters in length
    
    Args:
        uid (str): The UID to validate
        
    Returns:
        bool: True if the UID is valid, False otherwise
    """
    # Check if length is exactly 10
    if len(uid) != 10:
        return False
    
    # Check if all characters are alphanumeric
    if not uid.isalnum():
        return False
    
    # Check if any character repeats
    if len(set(uid)) != len(uid):
        return False
    
    # Count uppercase letters and digits
    uppercase_count = sum(1 for char in uid if char.isupper())
    digit_count = sum(1 for char in uid if char.isdigit())
    
    # Check if there are at least 2 uppercase letters and 3 digits
    if uppercase_count < 2 or digit_count < 3:
        return False
    
    return True

def main():
    # Read the number of test cases
    t = int(input().strip())
    
    # Process each test case
    for _ in range(t):
        uid = input().strip()
        
        if is_valid_uid(uid):
            print("Valid")
        else:
            print("Invalid")

if __name__ == "__main__":
    main()