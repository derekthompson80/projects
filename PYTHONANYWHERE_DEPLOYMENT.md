# Deploying to PythonAnywhere

This guide provides instructions for deploying the Flask applications in this project to PythonAnywhere.

## Prerequisites

1. A PythonAnywhere account (sign up at https://www.pythonanywhere.com/ if you don't have one)
2. Your project code uploaded to PythonAnywhere (via Git or manual upload)

## Configuration Steps

### 1. Set Up a Web App

1. Log in to your PythonAnywhere account
2. Go to the Web tab
3. Click "Add a new web app"
4. Choose "Manual configuration"
5. Select the Python version that matches your local environment (Python 3.8 or newer recommended)

### 2. Configure the WSGI File

1. In the Web tab, find the "Code" section and click on the WSGI configuration file link
2. Replace the contents with the code from the `wsgi.py` file in this project
3. Update the `project_home` path to match the location of your project on PythonAnywhere
   ```python
   project_home = '/home/your-username/path-to-your-project'
   ```
4. Choose which application to run by uncommenting the appropriate line:
   - For the Inspiring Quotes app:
     ```python
     application = inspiring_quotes_application
     # application = dereks_tasks_application
     ```
   - For the Derek's Tasks app:
     ```python
     # application = inspiring_quotes_application
     application = dereks_tasks_application
     ```
5. Save the file

### 3. Set Up the Virtual Environment

1. Open a Bash console in PythonAnywhere
2. Create a virtual environment:
   ```bash
   mkvirtualenv --python=/usr/bin/python3.8 myenv
   ```
3. Install the required packages:
   ```bash
   pip install flask requests google-api-python-client google-auth
   ```
   (Add any other dependencies your project requires)

### 4. Configure the Web App

1. In the Web tab, go to the "Virtualenv" section
2. Enter the path to your virtual environment (e.g., `/home/your-username/.virtualenvs/myenv`)
3. In the "Static Files" section, add:
   - URL: `/static/`
   - Path: `/home/your-username/path-to-your-project/inspiring_quotes/static/`
   (Add another entry for Derek's Tasks if needed)
4. Click the "Reload" button to apply the changes

### 5. Environment Variables

If your applications use environment variables, set them in the "WSGI configuration file":

1. In the Web tab, click on the WSGI configuration file link
2. Add your environment variables at the top of the file:
   ```python
   import os
   os.environ['NINJA_API_KEY'] = 'your-api-key'
   os.environ['YOUR_SPREADSHEET_ID'] = 'your-spreadsheet-id'
   # Add other environment variables as needed
   ```
3. Save the file

### 6. Service Account File

If you're using the Google Sheets API with a service account:

1. Upload your service account JSON file to PythonAnywhere
2. Make sure the path in `google_sheets_client.py` matches the location on PythonAnywhere

## Accessing Your Web Apps

Once deployed, your applications will be available at:

- `http://your-username.pythonanywhere.com/` (for whichever app is set as the default in the WSGI file)

## Troubleshooting

If you encounter issues:

1. Check the error logs in the Web tab
2. Ensure all dependencies are installed in your virtual environment
3. Verify that file paths in the WSGI file match your PythonAnywhere setup
4. Make sure environment variables are correctly set