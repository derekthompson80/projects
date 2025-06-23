from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import google_sheets_client as gsc  # Our Google Sheets client
import email_utils as eu  # Our email utility
import os
import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Needed for flashing messages

# Configure email recipient
EMAIL_RECIPIENT = "spade605@gmail.com"

# Store reminder settings
REMINDER_TIME = None
REMINDER_ACTIVE = False


@app.route('/')
def index():
    try:
        # Read columns A to F (Task to complete, Timeframe, Description, Recurring, Date, Completed)
        tasks_data = gsc.read_sheet_data(range_name='Sheet1!A:F')

        tasks_with_ids = []
        header = []
        if tasks_data:
            header = tasks_data[0]  # Keep the original header
            actual_tasks = tasks_data[1:] if len(tasks_data) > 1 else []

            for i, row in enumerate(actual_tasks):
                task_detail = {
                    'id': i + 2,  # Sheet rows are 1-indexed, +1 because we skipped header
                    'name': row[0] if len(row) > 0 else "N/A",
                    'timeframe': row[1] if len(row) > 1 else "N/A",
                    'description': row[2] if len(row) > 2 else "N/A",
                    'recurring': row[3] if len(row) > 3 else "N/A",
                    'due_date': row[4] if len(row) > 4 else "N/A",
                    'status': row[5] if len(row) > 5 else "N/A"  # 'Completed' column
                }
                tasks_with_ids.append(task_detail)

        return render_template('index.html', 
                              tasks=tasks_with_ids, 
                              header=header,
                              reminder_active=REMINDER_ACTIVE,
                              reminder_time=REMINDER_TIME)
    except Exception as e:
        flash(f"Error loading tasks: {e}", "error")
        return render_template('index.html', 
                              tasks=[], 
                              header=[],
                              reminder_active=REMINDER_ACTIVE,
                              reminder_time=REMINDER_TIME)


@app.route('/add_task', methods=['POST'])
def add_task():
    task_name = request.form.get('task_name')
    task_timeframe = request.form.get('task_timeframe', '')  # New field
    task_description = request.form.get('task_description', '')  # New field
    task_recurring = request.form.get('task_recurring', 'No')    # New field, default 'No'
    task_due_date = request.form.get('task_due_date', '')
    task_completed_status = request.form.get('task_completed', 'No')  # Default 'No' for new tasks

    if not task_name:
        flash('Task name is required!', 'error')
        return redirect(url_for('index'))

    # Order matches the sheet: Task, Timeframe, Description, Recurring, Due Date, Completed
    new_task_data = [[
        task_name,
        task_timeframe,
        task_description,
        task_recurring,
        task_due_date,
        task_completed_status
    ]]
    try:
        gsc.append_sheet_data(new_task_data, range_name='Sheet1!A1')  # Appends to the first table in Sheet1
        flash('Task added successfully!', 'success')

        # Send email notification for new task
        email_subject = f"New Task Added: {task_name}"
        email_body = (
            f"A new task has been added to the Google Sheet:\n\n"
            f"Task: {task_name}\n"
            f"Timeframe: {task_timeframe}\n"
            f"Description: {task_description}\n"
            f"Recurring: {task_recurring}\n"
            f"Due Date: {task_due_date}\n"
            f"Completed: {task_completed_status}"
        )
        eu.send_email(EMAIL_RECIPIENT, email_subject, email_body)

    except Exception as e:
        flash(f"Error adding task: {e}", "error")

    return redirect(url_for('index'))


@app.route('/set_reminder', methods=['POST'])
def set_reminder():
    global REMINDER_TIME, REMINDER_ACTIVE

    reminder_time = request.form.get('reminder_time')

    if not reminder_time:
        flash('Reminder time is required!', 'error')
        return redirect(url_for('index'))

    try:
        # Validate time format (HH:MM)
        datetime.datetime.strptime(reminder_time, '%H:%M')

        # Generate the email content
        subject = "Daily Task Reminder"
        body = "Here's your daily reminder to check your tasks!"

        # Schedule the daily reminder
        if eu.schedule_daily_reminder(EMAIL_RECIPIENT, reminder_time, subject, body):
            REMINDER_TIME = reminder_time
            REMINDER_ACTIVE = True
            flash(f'Daily reminder set for {reminder_time}!', 'success')
        else:
            flash('Failed to set reminder. Please try again.', 'error')
    except ValueError:
        flash('Invalid time format. Please use HH:MM (24-hour format).', 'error')
    except Exception as e:
        flash(f'Error setting reminder: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/cancel_reminder', methods=['POST'])
def cancel_reminder():
    global REMINDER_TIME, REMINDER_ACTIVE

    try:
        eu.cancel_all_reminders()
        REMINDER_TIME = None
        REMINDER_ACTIVE = False
        flash('Reminder cancelled successfully!', 'success')
    except Exception as e:
        flash(f'Error cancelling reminder: {e}', 'error')

    return redirect(url_for('index'))


@app.route('/get_reminder_status', methods=['GET'])
def get_reminder_status():
    return jsonify({
        'active': REMINDER_ACTIVE,
        'time': REMINDER_TIME
    })


@app.route('/update_status/<int:task_row_id>', methods=['POST'])
def update_task_status(task_row_id):
    new_status = request.form.get('new_status') # This will be 'Yes' or 'No' for 'Completed'
    # Fetch task name for email, assuming it's in the first column (A)
    # This requires an extra read, but is more robust than passing via form if not already there
    task_name_range = f'Sheet1!A{task_row_id}'
    task_name = "Unknown Task" # Default
    try:
        name_data = gsc.read_sheet_data(range_name=task_name_range)
        if name_data and name_data[0]:
            task_name = name_data[0][0]
    except Exception as e:
        print(f"Could not fetch task name for email: {e}")


    if not new_status:
        flash('New status is required!', 'error')
        return redirect(url_for('index'))

    # 'Completed' status is in Column F
    status_cell_range = f'Sheet1!F{task_row_id}'

    try:
        gsc.update_sheet_data(status_cell_range, [[new_status]])
        flash(f'Task "{task_name}" marked as "{new_status}"!', 'success')

        # Send email notification
        email_subject = f"Task Status Updated: {task_name}"
        email_body = f"The task '{task_name}' (row {task_row_id}) has been updated to: {new_status}."
        eu.send_email(EMAIL_RECIPIENT, email_subject, email_body)
    except Exception as e:
        flash(f"Error updating task status: {e}", "error")

    return redirect(url_for('index'))


@app.route('/send_daily_reminder', methods=['GET'])
def send_daily_reminder():
    global REMINDER_TIME, REMINDER_ACTIVE

    try:
        if REMINDER_ACTIVE and datetime.datetime.now().strftime('%H:%M') == REMINDER_TIME:
            # Read the task details for today
            tasks_data = gsc.read_sheet_data(range_name='Sheet1!A:F')
            today_tasks = [task for task in tasks_data[1:] if not task[5].strip()]  # Filter uncompleted tasks

            if today_tasks:
                message = "\n".join([f"Task: {task[0]}\nTimeframe: {task[1]}\nDescription: {task[2]}" for task in today_tasks])
                send_text_message('3025980093', message)
                flash("Daily reminder sent!", "success")
            else:
                flash("No uncompleted tasks to remind about.", "info")

        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error sending daily reminder: {e}", "error")
        return redirect(url_for('index'))


def initialize_reminder():
    """Initialize the daily reminder if REMINDER_TIME is set."""
    global REMINDER_TIME, REMINDER_ACTIVE

    # If a reminder time is already set, schedule it
    if REMINDER_TIME:
        try:
            subject = "Daily Task Reminder"
            body = "Here's your daily reminder to check your tasks!"

            if eu.schedule_daily_reminder(EMAIL_RECIPIENT, REMINDER_TIME, subject, body):
                REMINDER_ACTIVE = True
                print(f"Daily reminder initialized for {REMINDER_TIME}")
            else:
                print("Failed to initialize reminder")
        except Exception as e:
            print(f"Error initializing reminder: {e}")


if __name__ == '__main__':
    print("Starting Flask app...")
    print("Reminder: This application uses service account authentication for Google Sheets.")
    print(f"Ensure '{gsc.SERVICE_ACCOUNT_FILE}' is present.")
    print(
        "Configure SENDER_EMAIL and SENDER_PASSWORD in email_utils.py or as environment variables for email notifications.")

    # Set a default reminder time (9:00 AM)
    if not REMINDER_TIME:
        REMINDER_TIME = "09:00"
        initialize_reminder()
        print(f"Default daily reminder set for {REMINDER_TIME}")

    # When running locally, use debug mode and custom port
    # On PythonAnywhere, this script is imported so __name__ != '__main__'
    app.run(debug=True, port=5001)
