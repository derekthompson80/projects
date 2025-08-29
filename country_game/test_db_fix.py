import mysql.connector
from db_setup import config, create_database, create_tables

def test_db_fix():
    """Test the database fix"""
    try:
        print("Testing database fix...")

        # First try connecting without specifying a database
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)

        # Check if database exists
        cursor.execute("SHOW DATABASES LIKE 'spade605$county_game_server'")
        db_exists = cursor.fetchone()

        if db_exists:
            print(f"Database 'spade605$county_game_server' exists")

            # Use the database
            cursor.execute("USE spade605$county_game_server")

            # Check if tables exist
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]

            print(f"Tables in database: {', '.join(tables)}")

            # Check if stats table exists
            if 'stats' in tables:
                cursor.execute("SELECT COUNT(*) as count FROM stats")
                stats_count = cursor.fetchone()['count']
                print(f"Stats table has {stats_count} records")
            else:
                print("Stats table doesn't exist")
        else:
            print(f"Database 'spade605$county_game_server' doesn't exist")

        cursor.close()
        conn.close()

        # Now run the database setup
        print("\nRunning database setup...")
        create_database()

        # Connect again to verify changes
        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)

        # Check if database exists now
        cursor.execute("SHOW DATABASES LIKE 'spade605$county_game_server'")
        db_exists = cursor.fetchone()

        if db_exists:
            print(f"Database 'spade605$county_game_server' exists after setup")

            # Use the database
            cursor.execute("USE spade605$county_game_server")

            # Check if tables exist now
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]

            print(f"Tables in database after setup: {', '.join(tables)}")

            # Check if stats table exists and has data
            if 'stats' in tables:
                cursor.execute("SELECT COUNT(*) as count FROM stats")
                stats_count = cursor.fetchone()['count']
                print(f"Stats table has {stats_count} records after setup")
            else:
                print("Stats table doesn't exist after setup")
        else:
            print(f"Database 'county_game_local' doesn't exist after setup")

        cursor.close()
        conn.close()

        print("\nTest completed successfully!")

    except mysql.connector.Error as err:
        print(f"MySQL Error: {err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_db_fix()
