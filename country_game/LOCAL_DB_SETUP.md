# Local Database Setup for Testing

This document explains how to set up and use the local database for testing the Country Game application.

## Configuration

The database configuration has been updated to use a local MySQL server with the following settings:

- **Username**: root
- **Password**: Beholder30
- **Host**: localhost
- **Port**: 3306
- **Database Name**: county_game_local

## How to Use

1. Make sure you have MySQL installed on your local machine
2. Ensure the MySQL service is running
3. Run the test_db_connection.py script to verify the connection and create the database:
   ```
   python test_db_connection.py
   ```
4. If the connection is successful, you can proceed with using the application

## Switching Between Local and PythonAnywhere

When deploying to PythonAnywhere, you'll need to update the configuration in db_setup.py:

1. Change the DATABASE_NAME constant to 'spade605$county_game_server'
2. Update the config dictionary to use PythonAnywhere credentials:
   ```python
   config = {
       'user': 'spade605',
       'password': 'Beholder30',
       'host': 'spade605.mysql.pythonanywhere-services.com',
       'port': 3306,
       'raise_on_warnings': True
   }
   ```

## Troubleshooting

If you encounter connection issues:

1. Verify that MySQL is installed and running
2. Check that the username and password are correct
3. Ensure you have the necessary permissions to create databases
4. If using a different MySQL user, update the config in db_setup.py accordingly