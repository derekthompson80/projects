import sys
import os
import unittest
import requests
from unittest.mock import patch, MagicMock

# Add the current directory to the path so we can import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import the app and related objects from main.py
try:
    from main import app, db, Movie
    print("✓ Successfully imported app from main.py")
except ImportError as e:
    print(f"❌ Error importing from main.py: {e}")
    sys.exit(1)

class TestErrorHandling(unittest.TestCase):
    """Test the error handling in the find_movie route"""
    
    def setUp(self):
        """Set up the test client"""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    @patch('main.requests.get')
    def test_api_error(self, mock_get):
        """Test handling of API errors"""
        # Mock a failed API response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response
        
        # Make a request to the find_movie route
        response = self.client.get('/find/999999')
        
        # Check that we get a 200 response (the error page)
        self.assertEqual(response.status_code, 200)
        
        # Check that the error message is in the response
        self.assertIn(b"Failed to fetch movie details", response.data)
    
    @patch('main.requests.get')
    def test_incomplete_data(self, mock_get):
        """Test handling of incomplete movie data"""
        # Mock a successful API response but with incomplete data
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            # Missing title and overview
            "id": 12345,
            "release_date": "2023-01-01"
        }
        mock_get.return_value = mock_response
        
        # Make a request to the find_movie route
        response = self.client.get('/find/12345')
        
        # Check that we get a 200 response (the error page)
        self.assertEqual(response.status_code, 200)
        
        # Check that the error message is in the response
        self.assertIn(b"Incomplete movie data", response.data)
    
    @patch('main.requests.get')
    def test_network_error(self, mock_get):
        """Test handling of network errors"""
        # Mock a network error
        mock_get.side_effect = requests.RequestException("Connection error")
        
        # Make a request to the find_movie route
        response = self.client.get('/find/12345')
        
        # Check that we get a 200 response (the error page)
        self.assertEqual(response.status_code, 200)
        
        # Check that the error message is in the response
        self.assertIn(b"Network error", response.data)
    
    @patch('main.requests.get')
    def test_key_error(self, mock_get):
        """Test handling of KeyError"""
        # Mock a successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # The response has title and overview, but we'll force a KeyError in the route
        mock_response.json.return_value = {
            "title": "Test Movie",
            "overview": "Test description",
            # Missing release_date and poster_path, but we'll access them directly to trigger KeyError
        }
        mock_get.return_value = mock_response
        
        # Patch the Movie constructor to raise a KeyError
        with patch('main.Movie', side_effect=KeyError("release_date")):
            # Make a request to the find_movie route
            response = self.client.get('/find/12345')
            
            # Check that we get a 200 response (the error page)
            self.assertEqual(response.status_code, 200)
            
            # Check that the error message is in the response
            self.assertIn(b"incomplete or in an unexpected format", response.data)

if __name__ == "__main__":
    unittest.main()