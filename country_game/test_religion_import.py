import mysql.connector
import os
from db_setup import create_database, import_data

def test_religion_import():
    """Test that religions are properly imported into the database"""
    try:
        # First, ensure the database and tables are created
        create_database()
        import_data()

        # Connect to the database
        config = {
            'user': 'root',
            'password': 'Beholder30',
            'host': '127.0.0.1',
            'port': 3306,
            'database': 'county_game_local'
        }

        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)

        # Check if religions were imported
        cursor.execute("SELECT COUNT(*) as count FROM religions")
        result = cursor.fetchone()
        religion_count = result['count']

        print(f"Number of religions imported: {religion_count}")

        if religion_count > 0:
            # Display some sample religions
            cursor.execute("SELECT id, name, code, description FROM religions LIMIT 5")
            religions = cursor.fetchall()

            print("\nSample religions:")
            for religion in religions:
                print(f"ID: {religion['id']}, Name: {religion['name']}, Code: {religion['code']}")
                print(f"Description: {religion['description'][:100]}...")

                # Get entities for this religion
                cursor.execute("SELECT name, description FROM religion_entities WHERE religion_id = %s LIMIT 3", (religion['id'],))
                entities = cursor.fetchall()

                if entities:
                    print("Entities:")
                    for entity in entities:
                        print(f"  - {entity['name']}: {entity['description'][:50]}...")
                print()

            print("Religion import test completed successfully!")
        else:
            print("No religions were imported. Check the import process.")

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_religion_import()
