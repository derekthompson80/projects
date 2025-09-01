import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import sys
import os

# Add the current directory to the path so we can import db_setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from projects.country_game.country_game_utilites.db_setup import create_database, config, DATABASE_NAME

def test_admin_credentials():
    """Test that the admin credentials are correct"""
    print("Testing admin credentials...")
    
    try:
        # Connect to the database
        conn_config = config.copy()
        conn_config['database'] = DATABASE_NAME
        
        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE username = %s", ('admin',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"Admin user exists with ID: {admin_user['id']}")
            
            # Test password
            test_password = 'admin'
            if check_password_hash(admin_user['password'], test_password):
                print(f"Password verification successful for 'admin' user with password '{test_password}'")
            else:
                print(f"Password verification failed for 'admin' user with password '{test_password}'")
                
                # Recreate admin user with correct password
                print("Recreating admin user with correct password...")
                cursor.execute("DELETE FROM users WHERE username = %s", ('admin',))
                
                hashed_password = generate_password_hash('admin')
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    ('admin', hashed_password, 'staff')
                )
                conn.commit()
                print("Admin user recreated with password 'admin'")
        else:
            print("Admin user does not exist. Running database setup...")
            cursor.close()
            conn.close()
            
            # Run database setup to create admin user
            create_database()
            
            # Reconnect to verify
            conn = mysql.connector.connect(**conn_config)
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM users WHERE username = %s", ('admin',))
            admin_user = cursor.fetchone()
            
            if admin_user:
                print("Admin user created successfully")
                
                # Test password
                test_password = 'admin'
                if check_password_hash(admin_user['password'], test_password):
                    print(f"Password verification successful for 'admin' user with password '{test_password}'")
                else:
                    print(f"Password verification failed for 'admin' user with password '{test_password}'")
            else:
                print("Failed to create admin user")
        
        # Also check Derek.Thompson user
        cursor.execute("SELECT * FROM users WHERE username = %s", ('Derek.Thompson',))
        derek_user = cursor.fetchone()
        
        if derek_user:
            print(f"Derek.Thompson user exists with ID: {derek_user['id']}")
            
            # Test password
            test_password = 'Beholder30'
            if check_password_hash(derek_user['password'], test_password):
                print(f"Password verification successful for 'Derek.Thompson' user with password '{test_password}'")
            else:
                print(f"Password verification failed for 'Derek.Thompson' user with password '{test_password}'")
        else:
            print("Derek.Thompson user does not exist")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    test_admin_credentials()