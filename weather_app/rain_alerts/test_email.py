import sys
import os

# Since we're already in the project directory, we can import directly
from message_utils import send_weather_email

def test_email_sending():
    """Test sending a weather email."""
    print("Testing email sending functionality...")

    # Try to send an email with weather information for New York
    success = send_weather_email("New York")

    if success:
        print("Email sent successfully!")
    else:
        print("Failed to send email.")

if __name__ == "__main__":
    test_email_sending()
