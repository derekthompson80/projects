import tkinter as tk
from tkinter import messagebox

from weather_alerts_utils import kelvin_to_celsius, kelvin_to_fahrenheit, get_weather_forecast
from message_utils import send_weather_email, schedule_hourly_emails

from tkinter_util import root, fetch_button, clear_button, email_button, city_entry, result_text

# In a production environment, this should be stored in an environment variable
# or a configuration file that is not committed to version control
# Example: API_KEY = os.environ.get("OPENWEATHER_API_KEY")

# Define result_label as a function to update the text widget
def update_result_text(text):
    result_text.config(state=tk.NORMAL)
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, text)
    result_text.config(state=tk.DISABLED)

# Redefine result_label to use our function
class ResultLabel:
    def config(self, text=""):
        update_result_text(text)

result_label = ResultLabel()

def fetch_weather():
    try:
        # Disable buttons during loading to prevent multiple requests
        fetch_button.config(state=tk.DISABLED)
        clear_button.config(state=tk.DISABLED)

        # Show loading state
        result_label.config(text="Loading weather data...\nPlease wait...")
        root.update_idletasks()  # Force UI update

        # Get city name from entry field
        city_name = city_entry.get()

        # Validate input
        if not city_name:
            messagebox.showwarning("Warning", "Please enter a city name.")
            return

        weather_data = get_weather_forecast(city_name)

        if weather_data is not None and 'list' in weather_data:
            forecast_info = "Weather Forecast:\n"
            for forecast in weather_data['list'][:3]:  # Displaying first three forecasts
                try:
                    temp_kelvin = forecast['main']['temp']
                    temp_celsius = kelvin_to_celsius(temp_kelvin)
                    temp_fahrenheit = kelvin_to_fahrenheit(temp_kelvin)

                    forecast_info += f"Time: {forecast['dt_txt']}\n"
                    forecast_info += f"Temperature: {temp_celsius:.1f}°C / {temp_fahrenheit:.1f}°F\n"

                    if 'weather' in forecast and len(forecast['weather']) > 0:
                        forecast_info += f"Weather: {forecast['weather'][0]['description']}\n"

                    if 'wind' in forecast:
                        forecast_info += f"Wind: {forecast['wind'].get('speed', 'N/A')} m/s\n"

                    forecast_info += "\n"
                except KeyError as e:
                    forecast_info += f"Error parsing forecast data: {e}\n\n"

            result_label.config(text=forecast_info)
        else:
            messagebox.showerror("Error", "Failed to retrieve weather data or invalid data format")

    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
    finally:
        # Re-enable buttons regardless of success or failure
        fetch_button.config(state=tk.NORMAL)
        clear_button.config(state=tk.NORMAL)


# Function to clear all inputs and results
def clear_form():
    city_entry.delete(0, tk.END)
    city_entry.insert(0, "New York")  # Default city
    result_label.config(text="")


# Variable to track if email service is running
email_scheduler_running = False
email_scheduler_thread = None

# Function to toggle hourly email service
def toggle_email_service():
    global email_scheduler_running, email_scheduler_thread

    city_name = city_entry.get()
    if not city_name:
        messagebox.showwarning("Warning", "Please enter a city name.")
        return

    if not email_scheduler_running:
        try:
            # Send an immediate email
            if send_weather_email(city_name):
                # Start the hourly email service
                email_scheduler_thread = schedule_hourly_emails(city_name)
                email_scheduler_running = True
                email_button.config(text="Stop Hourly Emails", bg="#FF6347")  # Change to red
                messagebox.showinfo("Success", f"Hourly weather emails started for {city_name}.")
            else:
                messagebox.showerror("Error", "Failed to send initial email. Please check your settings.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start email service: {str(e)}")
    else:
        # There's no direct way to stop the thread in Python
        # We'll need to restart the application to stop it
        # But we can change the UI to reflect that it's "stopped"
        email_scheduler_running = False
        email_button.config(text="Start Hourly Emails", bg="#4CAF50")  # Change back to green
        messagebox.showinfo("Info", "Email service will be stopped when you close the application.")

# Set the command for the buttons
fetch_button.config(command=fetch_weather)
clear_button.config(command=clear_form)
email_button.config(command=toggle_email_service)



# Run the application
root.mainloop()
