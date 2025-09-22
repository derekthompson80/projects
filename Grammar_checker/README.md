# Google Docs Grammar Checker

A Flask web application that allows you to run grammar and spelling checks on your Google Docs using LanguageTool.

## Features

- Google OAuth authentication to access your Google Drive
- List all Google Docs in your Drive
- Process selected documents to check grammar and spelling
- View corrected text in the browser
- Download corrected text as a .txt file

## Prerequisites

- Python 3.6 or higher
- Google Cloud Platform account
- Google OAuth 2.0 credentials

## Setup

1. Clone the repository or download the source code.

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

   The requirements.txt file contains the following dependencies:
   - flask
   - google-auth-oauthlib
   - google-auth
   - google-api-python-client
   - python-docx (note: the package name is 'python-docx', not 'docx')
   - language-tool-python

3. Set up Google OAuth 2.0 credentials:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Google Drive API
   - Configure the OAuth consent screen
   - Create OAuth 2.0 credentials (Web application)
   - Add both `http://localhost:5000/oauth2callback` and `http://127.0.0.1:5000/oauth2callback` as authorized redirect URIs
   - Download the credentials JSON file
   - Rename it to `client_secret.json` and place it in the Grammar_checker directory

   OR

4. Use the template file:
   - Copy `client_secret_template.json` to `client_secret.json`
   - Open `client_secret.json` and replace the placeholder values with your actual credentials:
     - Replace `YOUR_CLIENT_ID` with your Google OAuth client ID
     - Replace `YOUR_PROJECT_ID` with your Google Cloud project ID
     - Replace `YOUR_CLIENT_SECRET` with your Google OAuth client secret

## Running the Application

1. Navigate to the Grammar_checker directory:
   ```
   cd Grammar_checker
   ```

2. Run the Flask application:
   ```
   python app.py
   ```

3. Open your web browser and go to `http://localhost:5000` or `http://127.0.0.1:5000`

4. Log in with your Google account

5. Select a Google Doc to process

6. View the corrected text and download it if needed

## How It Works

1. The application authenticates with Google using OAuth 2.0
2. It fetches a list of Google Docs from your Drive
3. When you select a document, it:
   - Downloads the document as a DOCX file
   - Processes it using LanguageTool to check grammar and spelling
   - Displays the corrected text in the browser
   - Allows you to download the corrected text as a .txt file

## Notes

- The application requires internet access to use the LanguageTool API
- SSL certificate verification is disabled for development purposes (not recommended for production)
- The application stores OAuth tokens in the session, which are cleared when you log out or close the browser
- The OAuth flow is configured to use the following parameters:
  - `access_type=offline`: Allows the application to refresh access tokens when they expire
  - `response_type=code`: Specifies that the authorization code flow should be used
  - `include_granted_scopes=true`: Includes previously granted scopes in the new authorization
  - The application supports both `localhost` and `127.0.0.1` as redirect URI hosts

## Troubleshooting

- If you encounter a `FileNotFoundError: [Errno 2] No such file or directory: 'client_secret.json'` error:
  - Make sure you've created the `client_secret.json` file as described in the Setup section
  - Verify that the file is in the correct location (in the Grammar_checker directory)
  - Check that the file contains valid JSON and the required OAuth credentials

- If you encounter other authentication errors, make sure your OAuth credentials are correctly set up
- If the application can't access your Google Docs, ensure you've granted the necessary permissions
- For any other issues, check the Flask server logs for error messages

### Optional database (MySQL over SSH)

This app can show blog entries from a MySQL database via an SSH tunnel. Database access is optional — if the DB dependencies are not installed or the connection fails, the app gracefully falls back to reading entries from local JSON files under `blog_entries/`.

To enable DB access, install the real packages from PyPI:

```
pip install paramiko sshtunnel
```

You also need a MySQL driver. On Windows, building `mysqlclient` can require extra build tools; a pure-Python fallback is available:

- Preferred (C extension, faster):
  ```
  pip install mysqlclient
  ```
- Fallback (pure Python):
  ```
  pip install PyMySQL
  ```

Important: Do NOT install packages named `paramiko-on-pypi` or `pycrypto-on-pypi`. Those are not the official packages and will fail to build on modern Python versions (e.g., Python 3.13). The project’s DB layer will automatically use `mysqlclient` if available, or fall back to `PyMySQL` if installed.
