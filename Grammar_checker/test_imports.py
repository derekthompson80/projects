# Test script to verify imports are working
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    print("All imports successful!")
except ImportError as e:
    print(f"Import error: {e}")