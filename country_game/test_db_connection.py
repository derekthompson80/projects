import mysql.connector
from db_setup import config, create_database, create_tables

def test_connection():
    """Test the database connection"""
    try:
        print("Attempting to connect to the database with the following configuration:")
        print(f"User: {config['user']}")
        print(f"Host: {config['host']}")
        print(f"Database: Not specified (connecting to server only)")
        
        # First try connecting to the server without specifying a database
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']
        
        conn = mysql.connector.connect(**conn_config)
        print("Successfully connected to the MySQL server!")
        
        # Check if we can create a database
        cursor = conn.cursor()
        print("\nAttempting to create database 'county_game_server'...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS county_game_server")
        print("Database created or already exists.")
        
        # Use the database
        cursor.execute("USE county_game_server")
        print("Using database 'county_game_server'")
        
        # Create tables
        print("\nAttempting to create tables...")
        create_tables(cursor)
        
        cursor.close()
        conn.close()
        print("\nDatabase connection test completed successfully!")
        return True
    
    except mysql.connector.Error as err:
        print(f"\nError: {err}")
        return False

if __name__ == "__main__":
    print("Testing database connection and setup...")
    if test_connection():
        print("\nNow running the full database setup...")
        create_database()
    else:
        print("\nDatabase connection test failed. Please check your configuration.")