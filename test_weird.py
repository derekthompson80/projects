import subprocess

# Test with input 5
print("Testing with n=5:")
result = subprocess.run(['python', 'weird.py'], 
                        input='5', 
                        text=True, 
                        capture_output=True)
print(f"Output: {result.stdout}")