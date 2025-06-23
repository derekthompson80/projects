import requests

from const_file import API_KEY

def kelvin_to_celsius(kelvin):
    return kelvin - 273.15

def kelvin_to_fahrenheit(kelvin):
    return (kelvin - 273.15) * 9/5 + 32


def get_weather_forecast(city_name):
    # Use the API key from the constant
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city_name}&appid={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None
