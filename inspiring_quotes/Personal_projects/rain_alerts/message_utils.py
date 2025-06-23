import smtplib
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from weather_alerts_utils import get_weather_forecast, kelvin_to_celsius, kelvin_to_fahrenheit

# Email configuration
SENDER_EMAIL = "Spade605@gmail.com"
RECEIVER_EMAIL = "spade605@gmail.com"
EMAIL_PASSWORD = "thua zbtz mkjf unox"
DEFAULT_CITY = "New York"

def format_weather_data(weather_data):
    """Format weather data into a readable email message."""
    if weather_data is None or 'list' not in weather_data:
        return "Failed to retrieve weather data."

    # Get the first forecast (current/nearest time)
    forecast = weather_data['list'][0]

    # Extract city name
    city_name = weather_data['city']['name'] if 'city' in weather_data and 'name' in weather_data['city'] else "Unknown"

    # Format the message
    message = f"Weather Update for {city_name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    try:
        temp_kelvin = forecast['main']['temp']
        temp_celsius = kelvin_to_celsius(temp_kelvin)
        temp_fahrenheit = kelvin_to_fahrenheit(temp_kelvin)

        message += f"Time: {forecast['dt_txt']}\n"
        message += f"Temperature: {temp_celsius:.1f}°C / {temp_fahrenheit:.1f}°F\n"

        if 'weather' in forecast and len(forecast['weather']) > 0:
            message += f"Weather: {forecast['weather'][0]['description']}\n"

        if 'main' in forecast:
            message += f"Humidity: {forecast['main'].get('humidity', 'N/A')}%\n"

        if 'wind' in forecast:
            message += f"Wind: {forecast['wind'].get('speed', 'N/A')} m/s\n"

    except KeyError as e:
        message += f"Error parsing forecast data: {e}\n"

    return message

def send_weather_email(city_name=DEFAULT_CITY):
    """Send an email with current weather information."""
    try:
        # Get weather data
        weather_data = get_weather_forecast(city_name)

        # Format the weather data
        email_body = format_weather_data(weather_data)

        # Create email
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = f"Weather Update for {city_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Attach the message
        msg.attach(MIMEText(email_body, 'plain'))

        # Create SMTP session
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            # Start TLS for security
            server.starttls()

            # Authentication
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)

            # Send the email
            server.send_message(msg)

        print(f"Weather email sent successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return True

    except Exception as e:
        print(f"Error sending weather email: {e}")
        return False

def schedule_hourly_emails(city_name=DEFAULT_CITY):
    """Schedule emails to be sent hourly."""
    def run_scheduler():
        while True:
            send_weather_email(city_name)
            # Sleep for 1 hour (3600 seconds)
            time.sleep(3600)

    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # Thread will exit when the main program exits
    scheduler_thread.start()

    print(f"Hourly weather emails scheduled for {city_name}")
    return scheduler_thread
