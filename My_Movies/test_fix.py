import requests
import logging
import time
import subprocess
import sys
import os
import signal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_flask_app():
    """Start the Flask app in a separate process."""
    logging.info("Starting Flask app...")
    flask_process = subprocess.Popen([sys.executable, "app.py"], 
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    # Give the app time to start
    time.sleep(2)
    return flask_process

def stop_flask_app(process):
    """Stop the Flask app process."""
    logging.info("Stopping Flask app...")
    os.kill(process.pid, signal.SIGTERM)
    process.wait()

def test_get_genres():
    """Test the get_genres endpoint."""
    url = "http://127.0.0.1:5080/get_genres"
    
    try:
        logging.info(f"Testing GET {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            genres = response.json()
            logging.info(f"Successfully fetched {len(genres)} genres")
            
            if genres:
                logging.info("Sample genres:")
                for i, genre in enumerate(genres[:5]):
                    logging.info(f"  {genre['name']} (ID: {genre['id']})")
                return True
            else:
                logging.error("No genres returned")
                return False
        else:
            logging.error(f"Failed to fetch genres. Status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error testing get_genres endpoint: {e}")
        return False

def test_get_movies():
    """Test the get_movies endpoint with a valid genre ID."""
    # Use Action genre (ID: 28) and year 2023 as a test
    url = "http://127.0.0.1:5080/get_movies?genre=28&year=2023"
    
    try:
        logging.info(f"Testing GET {url}")
        response = requests.get(url)
        
        if response.status_code == 200:
            movies = response.json()
            logging.info(f"Successfully fetched {len(movies)} movies")
            
            if movies:
                logging.info("Sample movies:")
                for i, movie in enumerate(movies[:3]):
                    logging.info(f"  {movie['title']} ({movie['release_date']})")
                return True
            else:
                logging.error("No movies returned")
                return False
        else:
            logging.error(f"Failed to fetch movies. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error testing get_movies endpoint: {e}")
        return False

def main():
    """Run all tests."""
    # Change to the directory containing app.py
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Start the Flask app
    flask_process = start_flask_app()
    
    try:
        # Run tests
        genres_success = test_get_genres()
        movies_success = test_get_movies()
        
        # Print summary
        logging.info("\nTest Summary:")
        logging.info(f"  Get Genres Test: {'PASSED' if genres_success else 'FAILED'}")
        logging.info(f"  Get Movies Test: {'PASSED' if movies_success else 'FAILED'}")
        
        if genres_success and movies_success:
            logging.info("\nAll tests PASSED! The fix was successful.")
        else:
            logging.info("\nSome tests FAILED. The fix may not be complete.")
    finally:
        # Stop the Flask app
        stop_flask_app(flask_process)

if __name__ == "__main__":
    main()