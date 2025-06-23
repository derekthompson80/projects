from flask import Flask, render_template, request, jsonify
import requests
import logging
from movies import API_KEY, READ_ACCESS_TOKEN, get_top_movies_by_genre, MOCK_GENRES

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_genres')
def get_genres():
    url = "https://api.themoviedb.org/3/genre/movie/list"
    params = {
        "api_key": API_KEY,
        "language": "en-US"
    }

    try:
        # Try to get genres from the API
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            if 'genres' in data and data['genres']:
                logging.info(f"Successfully fetched {len(data['genres'])} genres from API")
                # Return all genres directly from the API
                return jsonify(data['genres'])
            else:
                logging.warning("API response did not contain genres data")
        else:
            logging.error(f"Failed to fetch genres. Status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Error fetching genres from API: {e}")

    # If we get here, the API call failed or didn't return valid data
    # Fall back to mock data
    logging.info(f"Falling back to mock genres data. Returning {len(MOCK_GENRES)} genres.")
    return jsonify(MOCK_GENRES)

@app.route('/get_movies')
def get_movies():
    genre_id = request.args.get('genre')
    year = request.args.get('year')

    # Log the incoming request parameters
    logging.debug(f"Received GET /get_movies with genre_id: {genre_id}, year: {year}")

    if not genre_id:
        logging.error("No genre ID provided")
        return jsonify({"error": "No genre ID provided"}), 400

    try:
        # Convert genre_id to integer is now handled inside get_top_movies_by_genre
        movies = get_top_movies_by_genre(genre_id, year)

        if movies:
            # Log the result of get_top_movies_by_genre
            logging.debug(f"Found {len(movies)} movies for genre ID {genre_id} and year {year}")

            # Add poster path URL prefix for each movie
            for movie in movies:
                if movie.get('poster_path'):
                    movie['poster_path'] = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
                else:
                    movie['poster_path'] = "https://via.placeholder.com/500x750?text=No+Image+Available"

            return jsonify(movies)
        else:
            logging.error(f"No movies found for genre ID {genre_id} and year {year}")
            return jsonify({"error": "No movies found"}), 404
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(port=5076, debug=True)
