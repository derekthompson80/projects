import tkinter as tk

# Create the main window
root = tk.Tk()
root.title("Weather Forecast App")
root.geometry("500x500")
root.configure(padx=20, pady=20, bg="black")

# Create a frame for input fields
input_frame = tk.Frame(root, bg="black")
input_frame.pack(fill=tk.X, pady=10)

# City input
city_label = tk.Label(input_frame, text="City:", font=("Arial", 10, "bold"), bg="black", fg="white")
city_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
city_entry = tk.Entry(input_frame, width=25, bg="#333333", fg="white", insertbackground="white")
city_entry.grid(row=0, column=1, padx=5, pady=5)
city_entry.insert(0, "New York")  # Default city

# Button frame
button_frame = tk.Frame(root, bg="black")
button_frame.pack(fill=tk.X, pady=10)

# Fetch button (command will be set in main.py)
fetch_button = tk.Button(button_frame, text="Fetch Weather",
                         bg="#8A2BE2", fg="black", font=("Arial", 10, "bold"), padx=10)
fetch_button.pack(side=tk.LEFT, padx=5)

# Clear button (command will be set in main.py)
clear_button = tk.Button(button_frame, text="Clear",
                         bg="#8A2BE2", fg="black", font=("Arial", 10, "bold"), padx=10)
clear_button.pack(side=tk.LEFT, padx=5)

# Email button (command will be set in main.py)
email_button = tk.Button(button_frame, text="Start Hourly Emails",
                        bg="#4CAF50", fg="black", font=("Arial", 10, "bold"), padx=10)
email_button.pack(side=tk.LEFT, padx=5)

# Create a frame for results with scrollbar
result_frame = tk.Frame(root, bg="black")
result_frame.pack(fill=tk.BOTH, expand=True, pady=10)

# Add a scrollbar
scrollbar = tk.Scrollbar(result_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Result text widget instead of a label for better scrolling
result_text = tk.Text(result_frame, wrap=tk.WORD, height=15, width=50,
                      yscrollcommand=scrollbar.set, bg="gray", fg="black", padx=10, pady=10)
result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=result_text.yview)

# Make the text widget read-only
result_text.config(state=tk.DISABLED)
