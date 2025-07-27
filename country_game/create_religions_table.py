import mysql.connector

# Database name
DATABASE_NAME = 'county_game_local'

config = {
    'user': 'root',
    'password': 'Beholder30',
    'host': '127.0.0.1',
    'port': 3306,
    'database': DATABASE_NAME,
    'raise_on_warnings': True
}

def create_religions_tables():
    """Create the religions tables directly"""
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        print("Creating religions table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS religions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            code VARCHAR(10),
            description TEXT,
            parent_religion_id INT,
            FOREIGN KEY (parent_religion_id) REFERENCES religions(id)
        )
        """)
        
        print("Creating religion_entities table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS religion_entities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            religion_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            FOREIGN KEY (religion_id) REFERENCES religions(id)
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Religion tables created successfully")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    create_religions_tables()