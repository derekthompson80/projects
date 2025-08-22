def first_non_consecutive(arr):
    """
    Find the first element in the array that is not consecutive.
    
    A non-consecutive element is one that is not exactly 1 larger than the previous element.
    
    Args:
        arr (list): A list of numbers in ascending order
        
    Returns:
        int or None: The first non-consecutive number, or None if all elements are consecutive
                    or if the array has less than 2 elements
    """
    # Handle edge cases: empty array or array with a single element
    if len(arr) < 2:
        return None
    
    # Check each pair of adjacent elements
    for i in range(1, len(arr)):
        # If current element is not exactly 1 larger than the previous element
        if arr[i] != arr[i-1] + 1:
            return arr[i]
    
    # If all elements are consecutive
    return None


# Test cases
if __name__ == "__main__":
    # Example from the problem statement
    print(first_non_consecutive([1, 2, 3, 4, 6, 7, 8]))  # Should return 6
    
    # Additional test cases
    print(first_non_consecutive([1, 2, 3, 4, 5]))  # Should return None (all consecutive)
    print(first_non_consecutive([5, 6, 7, 8, 10]))  # Should return 10
    print(first_non_consecutive([-3, -2, 0, 1]))  # Should return 0
    print(first_non_consecutive([]))  # Should return None (empty array)
    print(first_non_consecutive([5]))  # Should return None (single element)
    print(first_non_consecutive([-5, -4, -3, -1]))  # Should return -1