import requests
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# TMDB API credentials
API_KEY = "2fa204374407eb54f2c53cb224286859"
READ_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIyZmEyMDQzNzQ0MDdlYjU0ZjJjNTNjYjIyNDI4Njg1OSIsIm5iZiI6MTc0ODI3NDIyOS4zODgsInN1YiI6IjY4MzQ4YzM1NWY2NDcwNTNlNzA1NTQ0YyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.PmxSgs32YXC5A9Khm1f5iVWqHCLYXmbc-7liHPh8O0E"

def test_get_genres_with_api_key():
    """Test fetching genres using API key in URL parameters."""
    url = "https://api.themoviedb.org/3/genre/movie/list"
    params = {
        "api_key": API_KEY,
        "language": "en-US"
    }
    
    try:
        logging.info("Testing genre fetch with API key in URL parameters...")
        response = requests.get(url, params=params, verify=False)
        logging.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"Success! Found {len(data['genres'])} genres.")
            return True
        else:
            logging.error(f"Failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error: {e}")
        return False

def test_get_genres_with_bearer_token():
    """Test fetching genres using Bearer token in Authorization header."""
    url = "https://api.themoviedb.org/3/genre/movie/list"
    headers = {
        "Authorization": f"Bearer {READ_ACCESS_TOKEN}"
    }
    params = {
        "language": "en-US"
    }
    
    try:
        logging.info("Testing genre fetch with Bearer token in Authorization header...")
        response = requests.get(url, headers=headers, params=params, verify=False)
        logging.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"Success! Found {len(data['genres'])} genres.")
            return True
        else:
            logging.error(f"Failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error: {e}")
        return False

def test_get_genres_with_both():
    """Test fetching genres using both API key and Bearer token."""
    url = "https://api.themoviedb.org/3/genre/movie/list"
    headers = {
        "Authorization": f"Bearer {READ_ACCESS_TOKEN}"
    }
    params = {
        "api_key": API_KEY,
        "language": "en-US"
    }
    
    try:
        logging.info("Testing genre fetch with both API key and Bearer token...")
        response = requests.get(url, headers=headers, params=params, verify=False)
        logging.info(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logging.info(f"Success! Found {len(data['genres'])} genres.")
            return True
        else:
            logging.error(f"Failed with status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing TMDB API authentication methods...")
    
    api_key_success = test_get_genres_with_api_key()
    bearer_token_success = test_get_genres_with_bearer_token()
    both_success = test_get_genres_with_both()
    
    print("\nResults:")
    print(f"API Key only: {'SUCCESS' if api_key_success else 'FAILED'}")
    print(f"Bearer Token only: {'SUCCESS' if bearer_token_success else 'FAILED'}")
    print(f"Both API Key and Bearer Token: {'SUCCESS' if both_success else 'FAILED'}")
    
    if api_key_success or bearer_token_success or both_success:
        print("\nAt least one authentication method worked!")
    else:
        print("\nAll authentication methods failed. Check your API credentials.")