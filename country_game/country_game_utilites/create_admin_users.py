import mysql.connector
from werkzeug.security import generate_password_hash

# Optionally load environment variables from a local .env file for credentials
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass

# Database connection parameters
config = {
    'user': 'root',
    'password': 'Darklove90!',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'spade605$county_game_server',
    'raise_on_warnings': True
}

def create_admin_users():
    """Create or update admin users with correct passwords"""
    try:
        # Connect to the database (optionally via SSH tunnel)
        import os
        use_tunnel = os.getenv('CG_USE_SSH_TUNNEL', 'false').lower() in ('1', 'true', 'yes')
        if use_tunnel:
            try:
                from projects.country_game.country_game_utilites.ssh_db_tunnel import get_connector_connection_via_tunnel
                conn, _close = get_connector_connection_via_tunnel(
                    db_user=config.get('user'),
                    db_password=config.get('password'),
                    db_name=config.get('database'),
                )
            except Exception:
                conn = mysql.connector.connect(**config)
        else:
            conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)
        
        # Check if admin user exists
        cursor.execute("SELECT * FROM users WHERE username = %s", ('admin',))
        admin_user = cursor.fetchone()
        
        if admin_user:
            print(f"Admin user exists with ID: {admin_user['id']}")
            print("Updating admin user password...")
            
            # Update admin password
            hashed_password = generate_password_hash('admin')
            cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (hashed_password, 'admin')
            )
            conn.commit()
            print("Admin user password updated to 'admin'")
        else:
            print("Admin user does not exist. Creating new admin user...")
            
            # Create admin user
            hashed_password = generate_password_hash('admin')
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ('admin', hashed_password, 'staff')
            )
            conn.commit()
            print("Admin user created with username 'admin' and password 'admin'")
        
        # Check if Derek.Thompson user exists
        cursor.execute("SELECT * FROM users WHERE username = %s", ('Derek.Thompson',))
        derek_user = cursor.fetchone()
        
        if derek_user:
            print(f"Derek.Thompson user exists with ID: {derek_user['id']}")
            print("Updating Derek.Thompson user password...")
            
            # Update Derek.Thompson password
            hashed_password = generate_password_hash('Beholder30')
            cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (hashed_password, 'Derek.Thompson')
            )
            conn.commit()
            print("Derek.Thompson user password updated to 'Beholder30'")
        else:
            print("Derek.Thompson user does not exist. Creating new user...")
            
            # Create Derek.Thompson user
            hashed_password = generate_password_hash('Beholder30')
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ('Derek.Thompson', hashed_password, 'staff')
            )
            conn.commit()
            print("Derek.Thompson user created with password 'Beholder30'")
        
        cursor.close()
        conn.close()
        print("Admin users setup completed successfully")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    create_admin_users()