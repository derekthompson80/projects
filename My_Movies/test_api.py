import requests
import json
import sys

def test_get_genres():
    print("Testing /get_genres endpoint...")
    response = requests.get("http://localhost:5001/get_genres")
    if response.status_code == 200:
        genres = response.json()
        print(f"Success! Found {len(genres)} genres.")
        if len(genres) > 0:
            print(f"Example genre: {genres[0]['name']} (ID: {genres[0]['id']})")
        return True
    else:
        print(f"Error: {response.status_code}")
        return False

def test_get_movies():
    print("\nTesting /get_movies endpoint...")
    # Use Action genre (ID: 28) and year 2023 as an example
    response = requests.get("http://localhost:5001/get_movies?genre=28&year=2023")
    if response.status_code == 200:
        movies = response.json()
        print(f"Success! Found {len(movies)} movies.")
        if len(movies) > 0:
            print(f"Example movie: {movies[0]['title']} (Release date: {movies[0]['release_date']})")
            print(f"Poster URL: {movies[0]['poster_path']}")
        return True
    else:
        print(f"Error: {response.status_code}")
        return False

if __name__ == "__main__":
    print("This script tests the API endpoints of the movie website.")
    print("Make sure the Flask application is running (python test_fix.py) before running this test.")
    print("Press Enter to continue or Ctrl+C to exit.")
    input()
    
    genres_success = test_get_genres()
    movies_success = test_get_movies()
    
    if genres_success and movies_success:
        print("\nAll tests passed! The website should be working correctly.")
    else:
        print("\nSome tests failed. Please check the error messages above.")