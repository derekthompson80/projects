import mysql.connector
import pandas as pd
import os
import csv

# MySQL connection parameters
config = {
    'user': 'root',
    'password': 'Beholder3',
    'host': 'localhost',
    'raise_on_warnings': True
}

def create_database():
    """Create the database and tables"""
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()

        # Create database
        cursor.execute("CREATE DATABASE IF NOT EXISTS county_game_server")
        print("Database created successfully")

        # Use the database
        cursor.execute("USE county_game_server")

        # Create tables
        create_tables(cursor)

        # Import werkzeug for password hashing
        from werkzeug.security import generate_password_hash

        # Check if the specified admin user already exists
        cursor.execute("SELECT * FROM users WHERE username = %s", ('admin',))
        admin_user = cursor.fetchone()

        if not admin_user:
            # Create admin user with specified credentials
            hashed_password = generate_password_hash('admin')
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ('admin', hashed_password, 'staff')
            )
            print("Created admin user (username: admin, password: admin)")

        # Check if the specified admin user already exists
        cursor.execute("SELECT * FROM users WHERE username = %s", ('Derek.Thompson',))
        admin_user = cursor.fetchone()

        if not admin_user:
            # Create admin user with specified credentials
            hashed_password = generate_password_hash('Beholder3')
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                ('Derek.Thompson', hashed_password, 'staff')
            )
            print("Created admin user (username: Derek.Thompson, password: Beholder3)")

        conn.commit()
        cursor.close()
        conn.close()
        print("Database setup completed successfully")

    except mysql.connector.Error as err:
        print(f"Error: {err}")

def create_tables(cursor):
    """Create the necessary tables"""
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        role VARCHAR(10) NOT NULL,
        country_db VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sender_id INT NOT NULL,
        recipient_id INT NOT NULL,
        subject VARCHAR(100) NOT NULL,
        content TEXT NOT NULL,
        is_read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users(id),
        FOREIGN KEY (recipient_id) REFERENCES users(id)
    )
    """)

    # Stats table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(50) NOT NULL,
        rating INT NOT NULL,
        modifier VARCHAR(10),
        notes TEXT,
        advisor VARCHAR(100)
    )
    """)

    # Resources table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        type VARCHAR(50),
        tier INT,
        natively_produced INT DEFAULT 0,
        trade INT DEFAULT 0,
        committed INT DEFAULT 0,
        not_developed INT DEFAULT 0,
        available INT DEFAULT 0
    )
    """)

    # Actions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS actions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        action_number INT NOT NULL,
        description TEXT,
        stat1 VARCHAR(50),
        stat1_value INT,
        stat2 VARCHAR(50),
        stat2_value INT,
        advisor_used BOOLEAN DEFAULT FALSE,
        resources_used TEXT,
        gold_spent INT DEFAULT 0
    )
    """)

    # Projects table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        effect TEXT,
        cost INT,
        resources TEXT,
        status CHAR(1),
        progress_per_turn INT DEFAULT 0,
        total_needed INT DEFAULT 0,
        total_progress INT DEFAULT 0,
        turn_started INT
    )
    """)

    print("Tables created successfully")

def import_data():
    """Import data from CSV files into the database"""
    try:
        # Connect to the database
        conn = mysql.connector.connect(**config, database='county_game_server')
        cursor = conn.cursor()

        # Import stats from player sheet
        with open('player_sheet_templete.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)

            # Extract stats (rows 5-13)
            for i in range(4, 13):
                if i < len(rows) and len(rows[i]) >= 3:
                    name = rows[i][0].strip()
                    if name and name != "Stat":
                        rating = int(rows[i][1]) if rows[i][1].isdigit() else 0
                        modifier = rows[i][2] if len(rows[i]) > 2 else None
                        notes = rows[i][3] if len(rows[i]) > 3 else None
                        advisor = rows[i][4] if len(rows[i]) > 4 else None

                        cursor.execute("""
                        INSERT INTO stats (name, rating, modifier, notes, advisor)
                        VALUES (%s, %s, %s, %s, %s)
                        """, (name, rating, modifier, notes, advisor))

        # Import resources from player sheet
        with open('player_sheet_templete.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)

            # Find the resources section
            resource_start = 0
            for i, row in enumerate(rows):
                if len(row) > 0 and row[0] == "Resources":
                    resource_start = i + 2  # Skip header row
                    break

            # Extract resources
            if resource_start > 0:
                for i in range(resource_start, len(rows)):
                    if i < len(rows) and len(rows[i]) >= 8:
                        name = rows[i][0].strip()
                        if name and name != "Name" and name != "":
                            resource_type = rows[i][1] if len(rows[i]) > 1 else None
                            tier = int(rows[i][2]) if len(rows[i]) > 2 and rows[i][2].isdigit() else 0
                            natively_produced = int(rows[i][3]) if len(rows[i]) > 3 and rows[i][3].isdigit() else 0
                            trade = int(rows[i][4]) if len(rows[i]) > 4 and rows[i][4].isdigit() else 0
                            committed = int(rows[i][5]) if len(rows[i]) > 5 and rows[i][5].isdigit() else 0
                            not_developed = int(rows[i][6]) if len(rows[i]) > 6 and rows[i][6].isdigit() else 0
                            available = int(rows[i][7]) if len(rows[i]) > 7 and rows[i][7].isdigit() else 0

                            cursor.execute("""
                            INSERT INTO resources (name, type, tier, natively_produced, trade, committed, not_developed, available)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (name, resource_type, tier, natively_produced, trade, committed, not_developed, available))

                            if i >= resource_start + 30:  # Limit to a reasonable number of resources
                                break

        # Import actions from player sheet
        with open('player_sheet_templete.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)

            # Find action sections
            for action_num in range(1, 5):  # Assuming up to 4 actions
                action_start = 0
                for i, row in enumerate(rows):
                    if len(row) > 0 and row[0] == f"Action {action_num}":
                        action_start = i
                        break

                if action_start > 0:
                    # Extract action description
                    description = ""
                    if action_start + 1 < len(rows) and len(rows[action_start + 1]) > 1:
                        description = rows[action_start + 1][1]

                    # Extract stats and resources
                    stats_row = 0
                    for i in range(action_start, len(rows)):
                        if len(rows[i]) > 0 and rows[i][0] == "Stat 1":
                            stats_row = i + 1
                            break

                    if stats_row > 0 and stats_row < len(rows):
                        stat1 = rows[stats_row][0] if len(rows[stats_row]) > 0 else None
                        stat1_value = int(rows[stats_row][1]) if len(rows[stats_row]) > 1 and rows[stats_row][1].isdigit() else 0
                        stat2 = rows[stats_row][2] if len(rows[stats_row]) > 2 else None
                        stat2_value = int(rows[stats_row][3]) if len(rows[stats_row]) > 3 and rows[stats_row][3].isdigit() else 0
                        advisor_used = True if len(rows[stats_row]) > 4 and rows[stats_row][4] == "Yes" else False

                        # Collect resources used
                        resources_used = []
                        for j in range(5, 10):
                            if len(rows[stats_row]) > j and rows[stats_row][j]:
                                resources_used.append(rows[stats_row][j])

                        gold_spent = int(rows[stats_row][10]) if len(rows[stats_row]) > 10 and rows[stats_row][10].isdigit() else 0

                        cursor.execute("""
                        INSERT INTO actions (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (action_num, description, stat1, stat1_value, stat2, stat2_value, advisor_used, ','.join(resources_used), gold_spent))

        # Import projects from staff sheet
        with open('staff_sheet_templete.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)

            # Find projects section
            project_start = 0
            for i, row in enumerate(rows):
                if len(row) > 0 and "Project A" in row:
                    project_start = i
                    break

            if project_start > 0:
                # Find column indices
                header_row = rows[project_start]
                name_col = header_row.index("Project A") if "Project A" in header_row else -1
                effect_col = header_row.index("Effect") if "Effect" in header_row else -1
                cost_col = header_row.index("Cost (g)") if "Cost (g)" in header_row else -1
                resources_col = header_row.index("Resource(s)") if "Resource(s)" in header_row else -1
                status_col = header_row.index("(O)ngoing (U)nfinished (S)uspended") if "(O)ngoing (U)nfinished (S)uspended" in header_row else -1
                progress_col = header_row.index("Progress Per Turn") if "Progress Per Turn" in header_row else -1
                needed_col = header_row.index("Total Needed") if "Total Needed" in header_row else -1
                total_col = header_row.index("Total Progress") if "Total Progress" in header_row else -1
                turn_col = header_row.index("Turn Started") if "Turn Started" in header_row else -1

                # Extract projects
                for i in range(project_start + 1, project_start + 9):  # Assuming up to 8 projects
                    if i < len(rows) and len(rows[i]) > name_col and rows[i][name_col]:
                        name = rows[i][name_col]
                        effect = rows[i][effect_col] if effect_col >= 0 and effect_col < len(rows[i]) else None
                        cost = int(rows[i][cost_col]) if cost_col >= 0 and cost_col < len(rows[i]) and rows[i][cost_col].isdigit() else 0
                        resources = rows[i][resources_col] if resources_col >= 0 and resources_col < len(rows[i]) else None
                        status = rows[i][status_col][0] if status_col >= 0 and status_col < len(rows[i]) and rows[i][status_col] else None
                        progress_per_turn = int(rows[i][progress_col]) if progress_col >= 0 and progress_col < len(rows[i]) and rows[i][progress_col].isdigit() else 0
                        total_needed = int(rows[i][needed_col]) if needed_col >= 0 and needed_col < len(rows[i]) and rows[i][needed_col].isdigit() else 0
                        total_progress = int(rows[i][total_col]) if total_col >= 0 and total_col < len(rows[i]) and rows[i][total_col].isdigit() else 0
                        turn_started = int(rows[i][turn_col]) if turn_col >= 0 and turn_col < len(rows[i]) and rows[i][turn_col].isdigit() else None

                        cursor.execute("""
                        INSERT INTO projects (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started))

        conn.commit()
        cursor.close()
        conn.close()
        print("Data imported successfully")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_database()
    import_data()
