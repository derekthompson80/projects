import smtplib
from email.mime.text import MIMEText
import os
import schedule
import time
import threading
import datetime

# --- Email Configuration ---
# It's highly recommended to use environment variables for sensitive data like email passwords.
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587  # For TLS
# Replace with your sender email or use environment variables
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'spade605@gmail.com')
# Replace with your App Password (if using Gmail with 2FA) or use environment variables
# Note: For Gmail with 2FA enabled, you MUST use an App Password, not your regular password
# Generate an App Password at: https://myaccount.google.com/apppasswords
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', 'balx uoto qxrc msba')

# Global variable to store the scheduler thread
scheduler_thread = None


def send_email(receiver_email, subject, body_text):
    """Sends an email using Gmail SMTP."""
    if SENDER_EMAIL == 'your_email@gmail.com' or SENDER_PASSWORD == 'your_app_password_here':
        print("Error: Sender email or password not configured in email_utils.py or environment variables.")
        print("Please update them to send emails.")
        return False

    msg = MIMEText(body_text)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        print(f"Email sent successfully to {receiver_email}!")
        return True
    except smtplib.SMTPAuthenticationError:
        print(f"SMTP Authentication Error: Failed to login with {SENDER_EMAIL}.")
        print("Please check your email and app password (if using Gmail with 2FA).")
        return False
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def schedule_daily_reminder(receiver_email, reminder_time, subject, body_text):
    """
    Schedule a daily email reminder at the specified time.

    Args:
        receiver_email (str): Email address to send the reminder to
        reminder_time (str): Time in 24-hour format (HH:MM)
        subject (str): Email subject
        body_text (str): Email body content

    Returns:
        bool: True if scheduling was successful, False otherwise
    """
    global scheduler_thread

    try:
        # Clear any existing schedules
        try:
            # Try to use clear() method if available in newer versions of schedule
            schedule.clear()
            print("Existing schedules cleared using schedule.clear()")
        except AttributeError:
            # Fall back to manual cancellation for older versions of schedule
            for job in schedule.get_jobs():
                schedule.cancel_job(job)
            print("Existing schedules cleared manually")

        # Schedule the email to be sent daily at the specified time
        schedule.every().day.at(reminder_time).do(
            send_email, receiver_email, subject, body_text
        )

        print(f"Daily email reminder scheduled for {reminder_time}")

        # Start the scheduler in a background thread if not already running
        if scheduler_thread is None or not scheduler_thread.is_alive():
            start_scheduler()

        return True
    except Exception as e:
        print(f"Error scheduling reminder: {e}")
        return False


def start_scheduler():
    """Start the scheduler in a background thread."""
    global scheduler_thread

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check for pending tasks every minute

    # Create and start the thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("Scheduler thread started")


def get_current_reminders():
    """
    Get a list of all currently scheduled reminders.

    Returns:
        list: List of scheduled jobs
    """
    return schedule.get_jobs()


def cancel_all_reminders():
    """Cancel all scheduled reminders."""
    try:
        # Try to use clear() method if available in newer versions of schedule
        schedule.clear()
        print("All reminders cancelled using schedule.clear()")
    except AttributeError:
        # Fall back to manual cancellation for older versions of schedule
        for job in schedule.get_jobs():
            schedule.cancel_job(job)
        print("All reminders cancelled manually")


if __name__ == '__main__':
    # Example usage (for testing this module directly)
    # Make sure to set SENDER_EMAIL and SENDER_PASSWORD environment variables or update them in the script.
    test_receiver = 'spade605@gmail.com'  # The user-specified email
    test_subject = 'Test Email from Python Task App'
    test_body = 'This is a test email to confirm the email sending functionality is working.'

    print(f"Attempting to send a test email to {test_receiver} from {SENDER_EMAIL}...")
    if send_email(test_receiver, test_subject, test_body):
        print("Test email function executed.")
    else:
        print("Test email function failed.")

    # Test scheduling a daily reminder
    print("\nTesting daily reminder scheduling...")
    current_time = datetime.datetime.now()
    test_time = (current_time + datetime.timedelta(minutes=1)).strftime("%H:%M")
    print(f"Scheduling a test reminder for 1 minute from now: {test_time}")

    if schedule_daily_reminder(
        test_receiver,
        test_time,
        "Daily Task Reminder",
        "This is your daily reminder to check your tasks!"
    ):
        print("Reminder scheduled successfully. The program will keep running to demonstrate the scheduler.")
        print("Press Ctrl+C to exit.")

        # Keep the main thread alive to allow the scheduler to run
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
    else:
        print("Failed to schedule reminder.")
