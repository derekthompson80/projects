# Import necessary libraries
import datetime
import os  # Needed for environment variables

# Try to import Google API libraries; fall back to a safe mock if unavailable
_GAPI_AVAILABLE = True
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except Exception:  # ImportError or environment without google libs
    _GAPI_AVAILABLE = False

    class HttpError(Exception):
        pass

    def build(*args, **kwargs):
        raise ImportError("google-api-python-client is not installed. Install it with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# --- Configuration ---
# Path to your Service Account JSON key file.
# **IMPORTANT**: Replace "your-actual-service-account-key-file.json" 
# with the actual filename of your downloaded Google Cloud service account key JSON file.
SERVICE_ACCOUNT_FILE = "service_account_file.json"  # <<< YOU MUST CHANGE THIS

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']  # Full read/write access

SPREADSHEET_ID = os.environ.get('YOUR_SPREADSHEET_ID', '1cAKXeige5AuGbiiLGuOOyb6hq3c2KLTtLFFdEQvkdn0')

# In-memory mock storage when Google APIs are unavailable
_MOCK_SHEET = [["Task", "Timeframe", "Description", "Recurring", "Date", "Completed"],
               ["Demo task", "Today", "Try the app", "No", datetime.date.today().isoformat(), "No"]]

# --- Authentication Function ---
def get_credentials():
    """Gets credentials for Google Sheets API using a Service Account."""
    if not _GAPI_AVAILABLE:
        # Google API libs not installed; signal to use mock
        return None
    creds = None
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"Error: Service account key file not found at {SERVICE_ACCOUNT_FILE}")
            print("Please ensure the file exists, the path is correct, and you have shared the Google Sheet with the service account email.")
            return None
        # Ensure the file being loaded is the correct JSON service account key
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    except ValueError as ve:  # Catch JSON decoding errors or wrong format errors
        print(f"Error loading service account credentials: {ve}")
        print(f"This usually means the file '{SERVICE_ACCOUNT_FILE}' is not a valid JSON service account key file, is empty, or is not the correct type of JSON file (e.g. missing fields like client_email, token_uri).")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading service account credentials: {e}")
        return None
    return creds

def _get_sheet_service():
    """Helper function to get the authenticated sheet service."""
    creds = get_credentials()
    if not creds:
        raise Exception("Could not authenticate with Google Sheets API using Service Account.")
    return build('sheets', 'v4', credentials=creds).spreadsheets()

def read_sheet_data(range_name: str):
    """Reads data from the specified range in the Google Sheet."""
    try:
        sheet_api = _get_sheet_service()
        result = sheet_api.values().get(spreadsheetId=SPREADSHEET_ID, range=range_name).execute()
        return result.get('values', [])
    except HttpError as err:
        print(f"An API error occurred while reading data: {err}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while reading data: {e}")
        raise

def append_sheet_data(values_to_append: list, range_name: str = 'Sheet1'):
    """Appends data to the specified sheet/range."""
    try:
        sheet_api = _get_sheet_service()
        body = {'values': values_to_append}
        result = sheet_api.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        print(f"Appended data. Updated range: {result.get('updates').get('updatedRange')}")
        return result
    except HttpError as err:
        print(f"An API error occurred while appending data: {err}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while appending data: {e}")
        raise

def update_sheet_data(range_name: str, values_to_update: list):
    """Updates data in the specified range in the Google Sheet."""
    try:
        sheet_api = _get_sheet_service()
        body = {'values': values_to_update}
        result = sheet_api.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        print(f"{result.get('updatedCells')} cells updated.")
        return result
    except HttpError as err:
        print(f"An API error occurred while updating data: {err}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred while updating data: {e}")
        raise

# --- Main Google Sheets Interaction (for testing this module directly) ---
def main_sheets_api_program():
    print("Attempting to test Google Sheets client functions using Service Account...")
    try:
        # Test read
        print("\nTesting read_sheet_data...")
        test_range_read = 'Sheet1!A1:C2' # Adjust if needed
        data = read_sheet_data(range_name=test_range_read)
        if data:
            print(f"Successfully read {len(data)} rows from {test_range_read}:")
            for row in data:
                print(row)
        else:
            print(f"No data found in {test_range_read} or an error occurred (check service account key and sheet sharing).")

        # Test append
        print("\nTesting append_sheet_data...")
        timestamp = str(datetime.datetime.now())
        test_values_append = [['Service Acct Test Append A at ' + timestamp, 'Service Acct Test Append B']]
        append_sheet_data(test_values_append, range_name='Sheet1') # Appends to the end of Sheet1
        print("Append test successful (check your sheet).")

        # Test update (be careful with the range, choose a safe cell for testing)
        print("\nTesting update_sheet_data...")
        test_range_update = 'Sheet1!H1' # Choose a safe cell to test update
        test_values_update = [['Updated via SA at ' + timestamp]]
        update_sheet_data(test_range_update, test_values_update)
        print(f"Update test successful for cell {test_range_update} (check your sheet).")

    except Exception as e:
        print(f"Error during direct test of google_sheets_client.py with Service Account: {e}")

if __name__ == '__main__':
    # Before running, make sure:
    # 1. You have enabled Google Sheets API in your Google Cloud Project.
    # 2. You have created a Service Account, downloaded its JSON key, and updated SERVICE_ACCOUNT_FILE.
    # 3. You have shared your Google Sheet with the Service Account's email address (with Editor permissions).
    # 4. SPREADSHEET_ID is correctly set (either directly or via YOUR_SPREADSHEET_ID env var).
    # 5. You have installed the required libraries:
    #    pip install google-api-python-client google-auth
    
    print(f"Using SPREADSHEET_ID: {SPREADSHEET_ID}")
    print(f"Service Account Key File: {SERVICE_ACCOUNT_FILE}") 
    
    main_sheets_api_program()