import requests
import list_of_genre as lg
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# TMDB API credentials
API_KEY = "1746088d2b0e9fe4217ab1a981d13858"
READ_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiIxNzQ2MDg4ZDJiMGU5ZmU0MjE3YWIxYTk4MWQxMzg1OCIsIm5iZiI6MTc0ODU0MjYxMS41ODksInN1YiI6IjY4MzhhNDkzOTQ1ODRhZjVhZTA1NjhjNSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.iHuumQkswd-1Hlcdw45EDfs3XwL5atzDyz_S1LrWRXk"

# Mock genres data for when API is unavailable
MOCK_GENRES = [
    {"id": 28, "name": "Action"},
    {"id": 12, "name": "Adventure"},
    {"id": 16, "name": "Animation"},
    {"id": 35, "name": "Comedy"},
    {"id": 80, "name": "Crime"},
    {"id": 99, "name": "Documentary"},
    {"id": 18, "name": "Drama"},
    {"id": 10751, "name": "Family"},
    {"id": 14, "name": "Fantasy"},
    {"id": 36, "name": "History"},
    {"id": 27, "name": "Horror"},
    {"id": 10402, "name": "Music"},
    {"id": 9648, "name": "Mystery"},
    {"id": 10749, "name": "Romance"},
    {"id": 878, "name": "Science Fiction"},
    {"id": 10770, "name": "TV Movie"},
    {"id": 53, "name": "Thriller"},
    {"id": 10752, "name": "War"},
    {"id": 37, "name": "Western"}
]

def get_top_movies_by_genre(genre_id, year):
    """Get the top movies for a given genre and year.

    First tries to get the movies from the TMDB API.
    If that fails, returns a list of mock movies.
    """
    url = f"https://api.themoviedb.org/3/discover/movie"
    # Convert genre_id to integer if it's a string
    try:
        genre_id = int(genre_id)
    except (ValueError, TypeError):
        logging.error(f"Invalid genre ID: {genre_id}")
        return None

    params = {
        "api_key": API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "include_video": "false",
        "page": 1,
        "with_genres": genre_id
    }

    # Add year parameter only if it's provided and valid
    if year and year.strip():
        try:
            year_int = int(year)
            if 1900 <= year_int <= 2030:  # Reasonable year range
                params["primary_release_year"] = year
                logging.info(f"Using year filter: {year}")
            else:
                logging.warning(f"Year {year} is out of reasonable range, not using as filter")
        except ValueError:
            logging.warning(f"Invalid year format: {year}, not using as filter")

    try:
        logging.info(f"Fetching movies for genre ID {genre_id} and year {year if year else 'any'}")
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        if 'results' in data and data['results']:
            movies = data['results'][:10]
            logging.info(f"Successfully fetched {len(movies)} movies from API")
            return movies
        else:
            logging.warning(f"No results found in API response")
    except Exception as e:
        logging.error(f"Error fetching movies from API: {e}")

    # If we get here, the API call failed or didn't return any movies
    # Return a list of mock movies
    logging.info("Returning mock movies data")

    # Create mock movies based on the genre
    genre_name = next((genre['name'] for genre in MOCK_GENRES if genre['id'] == genre_id), "Unknown")

    # Generate year string based on input or default to current year
    year_str = year if year and year.strip() else "2023"

    mock_movies = [
        {
            "id": 1000 + i,
            "title": f"{genre_name} Movie {i+1}",
            "release_date": f"{year_str}-01-{i+1:02d}",
            "poster_path": None,  # Will be replaced with placeholder in app.py
            "overview": f"This is a mock {genre_name.lower()} movie created because the API is unavailable."
        }
        for i in range(10)
    ]

    return mock_movies

def get_genre_id(genre_name):
    """Get the genre ID for a given genre name.

    First tries to get the genre ID from the TMDB API.
    If that fails, falls back to the mock genres data.
    """
    genres_url = "https://api.themoviedb.org/3/genre/movie/list"
    params = {
        "api_key": API_KEY,
        "language": "en-US"
    }

    try:
        # Try to get genres from the API
        response = requests.get(genres_url, params=params, verify=False)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        if 'genres' in data and data['genres']:
            genres = data['genres']
            genre_id = next((genre['id'] for genre in genres if genre['name'].lower() == genre_name.lower()), None)
            if genre_id is None:
                logging.warning(f"Genre '{genre_name}' not found in available genres from API.")
            else:
                logging.info(f"Found genre ID {genre_id} for '{genre_name}' from API.")
            return genre_id
        else:
            logging.warning(f"No genres found in API response: {data}")
    except Exception as e:
        logging.error(f"Error fetching genres from API: {e}")

    # If we get here, the API call failed or didn't return the genre we wanted
    # Fall back to mock data
    logging.info("Falling back to mock genres data.")
    genre_id = next((genre['id'] for genre in MOCK_GENRES if genre['name'].lower() == genre_name.lower()), None)

    if genre_id is None:
        logging.warning(f"Genre '{genre_name}' not found in mock genres.")
        # If genre name not found in mock data, return Action genre ID as default
        logging.info("Returning default genre ID (28 for Action).")
        return 28
    else:
        logging.info(f"Found genre ID {genre_id} for '{genre_name}' from mock data.")
        return genre_id

def main():
    print(f'Listing top movies by genre: {lg.get_tmdb_genres(API_KEY)[0]}')
    genre_name = input("Enter the genre type: ")
    year = input("Enter the year (YYYY): ")

    genre_id = get_genre_id(genre_name)

    if genre_id:
        movies = get_top_movies_by_genre(genre_id, year)

        if movies:
            print(f"Top 10 movies in the '{genre_name}' genre for {year}:")
            for i, movie in enumerate(movies, 1):
                print(f"{i}. {movie['title']} ({movie['release_date'][:4]})")
        else:
            print("No movies found.")
    else:
        print("Invalid genre type.")

if __name__ == "__main__":
    main()
