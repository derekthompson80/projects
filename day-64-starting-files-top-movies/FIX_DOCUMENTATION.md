# Flask-Bootstrap Compatibility Fix

## Issue Description
The application was encountering the following error when trying to run:

```
Traceback (most recent call last):
  File "C:\Users\spade\PyCharmMiscProject\projects\day-64-starting-files-top-movies\main.py", line 2, in <module>
    from flask_bootstrap import Bootstrap5
  File "C:\Users\spade\PyCharmMiscProject\.venv1\Lib\site-packages\flask_bootstrap\__init__.py", line 3, in <module>
    from flask import current_app, Markup, Blueprint, url_for
ImportError: cannot import name 'Markup' from 'flask' (C:\Users\spade\PyCharmMiscProject\.venv1\Lib\site-packages\flask\__init__.py)
```

## Root Cause
The error occurred because:
1. The application is using Flask 3.1.1, but the Flask-Bootstrap package (version 3.3.7.1) was trying to import `Markup` directly from `flask`.
2. In newer versions of Flask (2.0+), the `Markup` class was moved from the `flask` package to the `markupsafe` package.

## Solution Implemented
The fix involved modifying the Flask-Bootstrap package's `__init__.py` file to import `Markup` from `markupsafe` instead of `flask`:

```python
# Before
from flask import current_app, Markup, Blueprint, url_for

# After
from flask import current_app, Blueprint, url_for
from markupsafe import Markup
```

This change allows Flask-Bootstrap to work correctly with newer versions of Flask.

## Recommendations for Future Maintenance

1. **Package Version Management**:
   - Consider using a virtual environment specific to this project to avoid conflicts with other projects.
   - Pin exact versions of dependencies in `requirements.txt` to ensure consistent behavior.
   - The current `requirements.txt` specifies `Bootstrap_Flask==2.2.0`, but the code imports from `flask_bootstrap`. Consider updating either the import or the requirements to be consistent.

2. **Alternative Approaches**:
   - Consider migrating from Flask-Bootstrap to Bootstrap-Flask, which is more actively maintained and compatible with newer Flask versions.
   - If you choose to migrate, you'll need to update imports and possibly adjust templates to match the new package's API.

3. **Testing**:
   - After making changes to dependencies or their versions, thoroughly test the application to ensure all functionality works as expected.
   - Create automated tests for critical functionality to catch compatibility issues early.

4. **Documentation**:
   - Keep track of any modifications made to third-party packages, as these will need to be reapplied if the packages are reinstalled or updated.
   - Consider forking and maintaining your own version of problematic packages if they are critical to your application.