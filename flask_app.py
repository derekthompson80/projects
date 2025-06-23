# Import the Flask app from the Grammar_checker directory
import sys
import os

# Add Git cmd path to the PATH environment variable
git_cmd_paths = [
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files (x86)\Git\cmd"
]
for git_path in git_cmd_paths:
    if os.path.exists(git_path) and git_path not in os.environ["PATH"]:
        os.environ["PATH"] = git_path + os.pathsep + os.environ["PATH"]

# Add the Grammar_checker directory to the Python path
project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Grammar_checker')
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the Flask app
from app import app

# This file is used by the WSGI configuration to serve the application
if __name__ == '__main__':
    app.run(debug=False)
