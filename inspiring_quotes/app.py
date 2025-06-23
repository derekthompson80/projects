from flask import Flask, render_template
import requests
import os
import urllib3

# Suppress only the InsecureRequestWarning from urllib3 needed for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Define API URL.
riddles_API_URL =  'https://api.api-ninjas.com/v1/riddles'
# Get API key from environment variable or use default for development
ninja_key = os.environ.get('NINJA_API_KEY', "Yi9OGPEsHIDK39qCrIMvfg==J7L4CDxWFCeiVTNq")

# Initialize Flask.
# Set template_folder to match the actual directory name (template instead of templates)
app = Flask(__name__, template_folder='template')

# Define routing.
@app.route('/')
def index():
    # Make API Call using the defined API key.
    # Disable SSL verification to handle certificate issues
    # WARNING: This is not secure and should not be used in production.
    # For production, properly configure SSL certificates or use a trusted CA bundle.
    resp = requests.get(riddles_API_URL, headers={'X-Api-Key': ninja_key}, verify=False).json()
    # Get first riddle result since the API returns a list of results.
    riddle = resp[0]
    # Render HTML using the question and answer from the riddle.
    return render_template('index.html', question=riddle['question'], answer=riddle['answer'])

# Run the Flask app with debug mode enabled.
if __name__ == '__main__':
    app.run(debug=True)
