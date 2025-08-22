import requests
import sys
import os

# Add the current directory to the path so we can import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import the app and related objects from main.py
try:
    from main import app, db, Movie
    print("✓ Successfully imported app from main.py")
except ImportError as e:
    print(f"❌ Error importing from main.py: {e}")
    sys.exit(1)

def test_find_movie_route():
    """Test the find_movie route directly"""
    print("\nTesting find_movie route...")
    
    # Use a test movie ID from The Movie Database (Avatar)
    test_movie_id = 76600  # Avatar: The Way of Water
    
    # Create a test client
    with app.test_client() as client:
        # Make a request to the find_movie route
        print(f"Making request to /find/{test_movie_id}")
        response = client.get(f"/find/{test_movie_id}")
        
        # Check the response
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 302:  # Redirect status code
            print("✓ Route returned a redirect as expected")
            print(f"Redirect location: {response.location}")
            
            # Check if the redirect is to the edit page
            if 'edit' in response.location:
                print("✓ Redirects to the edit page as expected")
            else:
                print("❌ Unexpected redirect location")
        else:
            print("❌ Route did not return a redirect")
            print(f"Response data: {response.data}")

def test_api_request():
    """Test the API request directly"""
    print("\nTesting API request directly...")
    
    # Use a test movie ID from The Movie Database
    test_movie_id = 76600  # Avatar: The Way of Water
    
    # API key from main.py
    api_key = "1746088d2b0e9fe4217ab1a981d13858"
    
    # Make the API request
    movie_url = f"https://api.themoviedb.org/3/movie/{test_movie_id}"
    params = {
        "api_key": api_key
    }
    
    print(f"Making API request to {movie_url}")
    response = requests.get(movie_url, params=params)
    
    # Check the response
    print(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        movie_data = response.json()
        print("✓ API request successful")
        print(f"Movie title: {movie_data.get('title', 'Unknown')}")
        print(f"Release date: {movie_data.get('release_date', 'Unknown')}")
    else:
        print("❌ API request failed")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    # Run the tests
    test_api_request()
    
    # Only run the route test if the API test was successful
    with app.app_context():
        test_find_movie_route()