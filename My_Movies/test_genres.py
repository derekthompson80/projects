import requests
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_get_genres():
    """Test the get_genres endpoint to verify it's working correctly."""
    url = "http://127.0.0.1:5080/get_genres"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        if response.status_code == 200:
            genres = response.json()
            logging.info(f"Successfully fetched {len(genres)} genres")
            
            # Print the first few genres as an example
            for i, genre in enumerate(genres[:5]):
                logging.info(f"Genre {i+1}: {genre['name']} (ID: {genre['id']})")
                
            return True
        else:
            logging.error(f"Failed to fetch genres. Status code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error testing get_genres endpoint: {e}")
        return False

if __name__ == "__main__":
    print("Testing get_genres endpoint...")
    success = test_get_genres()
    
    if success:
        print("Test passed! Genres were successfully fetched.")
    else:
        print("Test failed! Could not fetch genres.")