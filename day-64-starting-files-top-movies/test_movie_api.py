import requests

def test_movie_search():
    """Test searching for movies using The Movie Database API"""
    api_key = "1746088d2b0e9fe4217ab1a981d13858"
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": api_key,
        "query": "Avatar"
    }
    
    print("Testing movie search API...")
    response = requests.get(search_url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        print(f"Search successful! Found {len(results)} movies.")
        
        if results:
            # Display the first 3 results
            for i, movie in enumerate(results[:3]):
                print(f"{i+1}. {movie['title']} ({movie['release_date'].split('-')[0] if movie.get('release_date') else 'Unknown'})")
                print(f"   ID: {movie['id']}")
                print(f"   Overview: {movie['overview'][:100]}...")
                print()
            
            # Test getting details for the first movie
            movie_id = results[0]["id"]
            test_movie_details(api_key, movie_id)
        else:
            print("No results found.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def test_movie_details(api_key, movie_id):
    """Test getting movie details using The Movie Database API"""
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": api_key
    }
    
    print(f"\nTesting movie details API for movie ID {movie_id}...")
    response = requests.get(movie_url, params=params)
    
    if response.status_code == 200:
        movie_data = response.json()
        print("Movie details retrieved successfully!")
        print(f"Title: {movie_data['title']}")
        print(f"Release Date: {movie_data['release_date']}")
        print(f"Overview: {movie_data['overview'][:100]}...")
        print(f"Poster Path: {movie_data.get('poster_path', 'None')}")
        
        # Construct the full image URL
        if movie_data.get('poster_path'):
            img_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"
            print(f"Full Image URL: {img_url}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_movie_search()