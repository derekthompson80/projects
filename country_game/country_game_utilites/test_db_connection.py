from projects.country_game.country_game_utilites.ssh_db_tunnel import connect_via_tunnel
from projects.country_game.country_game_utilites.db_setup import config, create_database, create_tables, DATABASE_NAME

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

        conn = connect_via_tunnel()
        if not conn:
            raise RuntimeError('Failed to connect via SSH tunnel')
        print("Successfully connected to the MySQL server via SSH tunnel!")

        # Check if we can create a database
        cursor = conn.cursor()
        print(f"\nAttempting to create database '{DATABASE_NAME}'...")
        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}")
            print("Database created or already exists.")
        except mysql.connector.Error as err:
            print(f"Note: {err}")
            print("Continuing with existing database...")

        # Use the database
        cursor.execute(f"USE {DATABASE_NAME}")
        print(f"Using database '{DATABASE_NAME}'")

        # Create tables
        print("\nAttempting to create tables...")
        try:
            create_tables(cursor)
            print("Tables created successfully.")
        except mysql.connector.Error as err:
            print(f"Note: {err}")
            print("Continuing with existing tables...")

        cursor.close()
        conn.close()
        print("\nDatabase connection test completed successfully!")
        return True

    except mysql.connector.Error as err:
        print(f"\nError: {err}")
        # If we got this far, we at least connected to the server
        if "already exists" in str(err):
            print("This is not a critical error - the database or tables already exist.")
            return True
        return False

if __name__ == "__main__":
    print("Testing database connection and setup...")
    if test_connection():
        print("\nNow running the full database setup...")
        create_database()
    else:
        print("\nDatabase connection test failed. Please check your configuration.")
