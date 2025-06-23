import requests
from requests.exceptions import SSLError

def get_tmdb_genres(api_key):
    url = "https://api.themoviedb.org/3/genre/movie/list"
    params = {
        "api_key": api_key,
        "language": "en-US"
    }

    try:
        response = requests.get(url, params=params, verify=False)
        response.raise_for_status()
        genres =  response.json()["genres"]
        return [[d.get('name') for d in genres]]
    except SSLError as e:
        return f"SSL Error: {e}"
    except Exception as e:
        return f"Error fetching genres: {e}"


