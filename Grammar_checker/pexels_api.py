"""
Module for interacting with the Pexels API to search for images and videos.
"""
import requests
import json

class PexelsAPI:
    """
    A class to interact with the Pexels API for searching images and videos.
    """

    def __init__(self, api_key):
        """
        Initialize the PexelsAPI with the given API key.

        Args:
            api_key (str): The Pexels API key
        """
        self.api_key = api_key
        self.headers = {
            'Authorization': api_key
        }
        self.base_url = 'https://api.pexels.com/v1'
        self.video_url = 'https://api.pexels.com/videos'

    def search_photos(self, query, per_page=10, page=1):
        """
        Search for photos on Pexels.

        Args:
            query (str): The search query
            per_page (int, optional): Number of results per page. Defaults to 10.
            page (int, optional): Page number. Defaults to 1.

        Returns:
            dict: The API response containing photo results
        """
        url = f"{self.base_url}/search"
        params = {
            'query': query,
            'per_page': per_page,
            'page': page
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching photos: {str(e)}")
            return {'photos': []}

    def search_videos(self, query, per_page=10, page=1):
        """
        Search for videos on Pexels.

        Args:
            query (str): The search query
            per_page (int, optional): Number of results per page. Defaults to 10.
            page (int, optional): Page number. Defaults to 1.

        Returns:
            dict: The API response containing video results
        """
        url = f"{self.video_url}/search"
        params = {
            'query': query,
            'per_page': per_page,
            'page': page
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error searching videos: {str(e)}")
            return {'videos': []}

    def get_photo_by_id(self, photo_id):
        """
        Get a specific photo by its ID.

        Args:
            photo_id (str): The ID of the photo

        Returns:
            dict: The photo data
        """
        url = f"{self.base_url}/photos/{photo_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting photo: {str(e)}")
            return None

    def get_video_by_id(self, video_id):
        """
        Get a specific video by its ID.

        Args:
            video_id (str): The ID of the video

        Returns:
            dict: The video data
        """
        url = f"{self.video_url}/videos/{video_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting video: {str(e)}")
            return None
