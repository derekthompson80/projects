import subprocess
import os
import sys

def test_git_command():
    try:
        # Print current PATH for debugging
        print("Current PATH:", os.environ.get("PATH", ""))
        
        # Try to execute 'git --version' command
        result = subprocess.run(['git', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               check=True)
        
        # Print the output
        print("Git command executed successfully:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("Error executing git command:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Git command not found. Make sure Git is installed and in the PATH.")
        return False

if __name__ == "__main__":
    # First, import the flask_app to ensure Git path is added to PATH
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import flask_app
    
    # Test if git command works
    success = test_git_command()
    
    if success:
        print("Git path is correctly configured in the Python environment.")
    else:
        print("Failed to execute Git command. Please check the Git installation and PATH configuration.")