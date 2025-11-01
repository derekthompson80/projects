# This file contains the WSGI configuration required to serve up your
# web application at http://<your-username>.pythonanywhere.com/
# It works by setting the variable 'application' to a WSGI handler of some
# description.
#
# The below has been auto-generated for your Flask project

import sys
import os

# Add Git cmd path to the PATH environment variable
# For Linux/PythonAnywhere environment
git_cmd_paths = [
    "/usr/bin",  # Common location for git on Linux
    "/usr/local/bin"  # Alternative location
]
for git_path in git_cmd_paths:
    if os.path.exists(git_path) and git_path not in os.environ.get("PATH", ""):
        os.environ["PATH"] = git_path + os.pathsep + os.environ.get("PATH", "")

# add your project directory to the sys.path
project_home = '/home/spade605/Derek_person_projects/Blog'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# import flask app but need to call it "application" for WSGI to work
from app import app as application  # noqa
