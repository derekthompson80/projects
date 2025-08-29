import mysql.connector
import os
import csv
import sys

# Optionally load environment variables from a local .env file for credentials
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Database connection parameters - using the same config as db_setup.py
DATABASE_NAME = 'spade605$county_game_server'

config = {
    'user': 'root',
    'password': 'Darklove90!',
    'host': '127.0.0.1',
    'port': 3306,
    'raise_on_warnings': True
}

# Import db_setup to ensure database exists
sys.path.append(SCRIPT_DIR)
import db_setup

def import_religions_from_csv():
    """Import religions data from the CSV file into the database"""
    try:
        # Ensure database exists by running db_setup functions
        print("Ensuring database exists...")
        db_setup.create_database()
        
        # Connect to the database with updated config including database name
        conn_config = config.copy()
        conn_config['database'] = DATABASE_NAME
        
        # Connect to the database (optionally via SSH tunnel)
        use_tunnel = os.getenv('CG_USE_SSH_TUNNEL', 'false').lower() in ('1', 'true', 'yes')
        if use_tunnel:
            try:
                from projects.country_game.ssh_db_tunnel import get_connector_connection_via_tunnel
                conn, _close = get_connector_connection_via_tunnel(
                    db_user=conn_config.get('user'),
                    db_password=conn_config.get('password'),
                    db_name=conn_config.get('database'),
                )
            except Exception:
                conn = mysql.connector.connect(**conn_config)
        else:
            conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()
        
        # Check if the religions table exists
        cursor.execute("SHOW TABLES LIKE 'religions'")
        if not cursor.fetchone():
            print("Religions table doesn't exist. Creating tables...")
            db_setup.create_tables(cursor)
            conn.commit()
        
        # Clear existing data from the religions and religion_entities tables
        cursor.execute("DELETE FROM religion_entities")
        cursor.execute("DELETE FROM religions")
        conn.commit()
        print("Cleared existing religion data from the database.")
        
        # Read the CSV file
        csv_path = os.path.join(SCRIPT_DIR, 'religions.csv')
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            
            # Skip the header row
            header = next(csv_reader)
            
            # Process each row
            for row in csv_reader:
                if len(row) >= 3:  # Ensure we have at least name, abbreviation, and description
                    religion_name = row[0].strip()
                    abbreviation = row[1].strip() if row[1] else None
                    description = row[2].strip() if len(row) > 2 else None
                    
                    # Skip empty rows
                    if not religion_name:
                        continue
                    
                    # Insert into religions table
                    cursor.execute("""
                    INSERT INTO religions (name, code, description)
                    VALUES (%s, %s, %s)
                    """, (religion_name, abbreviation, description))
                    
                    # Get the ID of the inserted religion
                    religion_id = cursor.lastrowid
                    
                    # If this is a deity/entity rather than a main religion, we could detect it
                    # based on certain patterns in the data and insert it into religion_entities
                    # For now, we're treating all rows as main religions
            
            conn.commit()
            print(f"Successfully imported religions from {csv_path}")
        
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import_religions_from_csv()
    print("Religion import completed.")