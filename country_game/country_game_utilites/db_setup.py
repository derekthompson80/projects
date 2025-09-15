import os
import csv

# Optionally load environment variables from a local .env file for credentials
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv(), override=False)
except Exception as e:
    if __name__ == "__main__":
        print(f"Warning: Error loading environment variables from .env file: {e}")

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_database():
    """Create the database and tables"""
    try:
        # Connect to the remote database via SSH tunnel only

        # Connect to MySQL exclusively via SSH tunnel to the remote DB
        from projects.country_game.country_game_utilites.ssh_db_tunnel import connect_via_tunnel
        conn = connect_via_tunnel()
        if conn is None:
            raise RuntimeError("Failed to connect to remote database via SSH tunnel")
        _close = lambda: None  # kept for compatibility with the previous flow
        cursor = conn.cursor()

        # We are already connected to the target database via the tunnel; just ensure tables exist
        create_tables(cursor)

        # Import werkzeug for password hashing
        from werkzeug.security import generate_password_hash

        # Create an initial staff user from environment variables if provided
        admin_username = os.getenv('CG_ADMIN_USERNAME')
        admin_password = os.getenv('CG_ADMIN_PASSWORD')
        if admin_username and admin_password:
            cursor.execute("SELECT * FROM users WHERE username = %s", (admin_username,))
            existing = cursor.fetchone()
            if not existing:
                hashed_password = generate_password_hash(admin_password)
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                    (admin_username, hashed_password, 'staff')
                )
                print(f"Created admin user (username: {admin_username}) from environment variables")
        else:
            print("No CG_ADMIN_USERNAME/CG_ADMIN_PASSWORD provided; skipping admin creation.")

        conn.commit()
        cursor.close()
        try:
            conn.close()
        except Exception:
            pass
        _close()
        print("Database setup completed successfully")

    except Exception as err:
        print(f"Error: {err}")

def create_tables(cursor):
    """Create the necessary tables"""

    # Function to check if a column exists in a table
    def column_exists(cursor, table, column):
        cursor.execute(f"""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
        AND TABLE_NAME = '{table}'
        AND COLUMN_NAME = '{column}'
        """)
        return cursor.fetchone()[0] > 0
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
        rating INT NOT NULL
    )
    """)

    # Resources table (legacy columns retained); ensure CG5 columns exist and backfill
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        type VARCHAR(50),
        level INT NULL,
        description TEXT NULL
    )
    """)

    # Add missing CG5 columns if upgrading an existing DB
    try:
        if not column_exists(cursor, 'resources', 'level'):
            cursor.execute("ALTER TABLE resources ADD COLUMN level INT NULL AFTER type")
        if not column_exists(cursor, 'resources', 'description'):
            cursor.execute("ALTER TABLE resources ADD COLUMN description TEXT NULL AFTER level")
    except Exception as _e:
        print(f"Warning: could not ensure CG5 columns on resources: {_e}")

    # Backfill level from tier when level is NULL
    try:
        cursor.execute("UPDATE resources SET level = COALESCE(level, tier)")
    except Exception as _e:
        print(f"Warning: could not backfill level from tier: {_e}")

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
        gold_spent INT DEFAULT 0,
        is_free BOOLEAN DEFAULT FALSE,
        staff_response TEXT,
        response_date TIMESTAMP NULL
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
        turn_started INT,
        winter_storage BOOLEAN DEFAULT FALSE
    )
    """)

    # Seasons table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name ENUM('Spring', 'Summer', 'Fall', 'Winter') NOT NULL,
        year INT NOT NULL,
        current BOOLEAN DEFAULT FALSE,
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date TIMESTAMP,
        effects TEXT
    )
    """)

    # Achievements table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        country_id VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        progress INT DEFAULT 0,
        total_needed INT DEFAULT 100,
        completed BOOLEAN DEFAULT FALSE
    )
    """)

    # Events table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        region VARCHAR(100),
        affected_countries TEXT,
        start_season_id INT,
        duration INT DEFAULT 1,
        effects TEXT,
        active BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (start_season_id) REFERENCES seasons(id)
    )
    """)

    # Country exceptions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS country_exceptions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        country_id VARCHAR(100) NOT NULL,
        rule_type VARCHAR(50) NOT NULL,
        description TEXT NOT NULL,
        effect TEXT
    )
    """)

    # Standard actions (default actions) table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS standard_actions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        project VARCHAR(255) NOT NULL,
        stat_type VARCHAR(50),
        points_cost VARCHAR(50),
        resource_costs TEXT,
        requirements TEXT,
        benefits TEXT
    )
    """)


    # Countries table (new central registry for countries)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        ruler_name VARCHAR(100) NOT NULL,
        government_type VARCHAR(50),
        description TEXT,
        db_name VARCHAR(128),
        assigned_player_id INT NULL,
        is_open_for_selection BOOLEAN DEFAULT TRUE,
        politics INT,
        military INT,
        economics INT,
        culture INT,
        resources_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_player_id) REFERENCES users(id)
    )
    """)

    # Check if politics column exists and add it if it doesn't
    if not column_exists(cursor, 'countries', 'politics'):
        print("Adding missing 'politics' column to countries table")
        cursor.execute("ALTER TABLE countries ADD COLUMN politics INT")

    # Check if military column exists and add it if it doesn't
    if not column_exists(cursor, 'countries', 'military'):
        print("Adding missing 'military' column to countries table")
        cursor.execute("ALTER TABLE countries ADD COLUMN military INT")

    # Check if economics column exists and add it if it doesn't
    if not column_exists(cursor, 'countries', 'economics'):
        print("Adding missing 'economics' column to countries table")
        cursor.execute("ALTER TABLE countries ADD COLUMN economics INT")

    # Check if culture column exists and add it if it doesn't
    if not column_exists(cursor, 'countries', 'culture'):
        print("Adding missing 'culture' column to countries table")
        cursor.execute("ALTER TABLE countries ADD COLUMN culture INT")

    # Check if resources_json column exists and add it if it doesn't
    if not column_exists(cursor, 'countries', 'resources_json'):
        print("Adding missing 'resources_json' column to countries table")
        cursor.execute("ALTER TABLE countries ADD COLUMN resources_json TEXT")

    print("Tables created successfully")

def import_data():
    """Import data from CSV files into the database"""
    try:
        # Connect to the remote database via SSH tunnel only
        from projects.country_game.country_game_utilites.ssh_db_tunnel import connect_via_tunnel
        conn = connect_via_tunnel()
        if conn is None:
            raise RuntimeError("Failed to connect to remote database via SSH tunnel")
        _close = lambda: None
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        if 'stats' not in tables or 'users' not in tables or 'resources' not in tables:
            print("Required tables don't exist. Creating tables first...")
            create_tables(cursor)

        # Reset cursor to non-dictionary mode for data import
        cursor.close()
        cursor = conn.cursor()

        # Check if stats table has data
        cursor.execute("SELECT COUNT(*) FROM stats")
        stats_count = cursor.fetchone()[0]

        if stats_count == 0:
            print("Importing stats data...")
            # Import stats from a player sheet
            try:
                with open(os.path.join(SCRIPT_DIR, 'player_sheet_templete.csv'), 'r') as file:
                    reader = csv.reader(file)
                    rows = list(reader)

                    # Extract stats (rows 5-13)
                    for i in range(4, 13):
                        if i < len(rows) and len(rows[i]) >= 3:
                            name = rows[i][0].strip()
                            if name and name != "Stat":
                                rating = 0

                                cursor.execute("""
                                INSERT INTO stats (name, rating)
                                VALUES (%s, %s, %s, %s, %s)
                                """, (name, rating))
            except FileNotFoundError:
                print("Warning: player_sheet_templete.csv not found. Skipping stats import.")
        else:
            print(f"Stats table already has {stats_count} records. Skipping import.")

        # Check if resources table has data
        cursor.execute("SELECT COUNT(*) FROM resources")
        resources_count = cursor.fetchone()[0]

        if resources_count == 0:
            print("Importing resources data from cg5_resources.csv...")
            # Prefer CG5 resources CSV
            try:
                with open(os.path.join(SCRIPT_DIR, 'cg5_resources.csv'), 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        name = (row.get('name') or '').strip()
                        if not name:
                            continue
                        rtype = (row.get('type') or '').strip()
                        description = (row.get('description') or '').strip()
                        # Some CSVs may use 'level' or 'tier'
                        level_str = (row.get('level') or row.get('tier') or '').strip()
                        try:
                            level = int(level_str) if level_str.isdigit() else None
                        except Exception:
                            level = None
                        cursor.execute(
                            """
                            INSERT INTO resources (name, type, level, description)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (name, rtype, level, description)
                        )
                print("CG5 resources imported.")
            except FileNotFoundError:
                print("Warning: cg5_resources.csv not found. Falling back to player_sheet_templete.csv for legacy import.")
                # Legacy fallback from player sheet
                try:
                    with open(os.path.join(SCRIPT_DIR, 'player_sheet_templete.csv'), 'r') as file:
                        reader = csv.reader(file)
                        rows = list(reader)
                        resource_start = 0
                        for i, row in enumerate(rows):
                            if len(row) > 0 and row[0] == "Resources":
                                resource_start = i + 2
                                break
                        if resource_start > 0 and resource_start < len(rows):
                            try:
                                for i in range(resource_start, len(rows)):
                                    if i < len(rows) and len(rows[i]) >= 8:
                                        try:
                                            name = rows[i][0].strip() if rows[i][0] is not None else ""
                                            if name and name != "Name" and name != "":
                                                rtype = rows[i][1] if len(rows[i]) > 1 and rows[i][1] is not None else None
                                                try:
                                                    tier = int(rows[i][2]) if len(rows[i]) > 2 and rows[i][2] is not None and rows[i][2].isdigit() else 0
                                                except (ValueError, AttributeError):
                                                    tier = 0
                                                cursor.execute(
                                                    """
                                                    INSERT INTO resources (name, type, tier, level)
                                                    VALUES (%s, %s, %s, %s)
                                                    """,
                                                    (name, rtype, tier, tier)
                                                )
                                        except IndexError as e:
                                            print(f"Warning: Error processing resource row {i}: {e}")
                                            continue
                                        if i >= resource_start + 30:
                                            break
                            except Exception as e:
                                print(f"Warning: Error processing resources: {e}")
                except FileNotFoundError:
                    print("Warning: player_sheet_templete.csv not found. Skipping resources import.")
        else:
            print(f"Resources table already has {resources_count} records. Skipping import.")

        # Check if actions table has data
        cursor.execute("SELECT COUNT(*) FROM actions")
        actions_count = cursor.fetchone()[0]

        if actions_count == 0:
            print("Importing actions data...")
            # Import actions from player sheet
            try:
                with open(os.path.join(SCRIPT_DIR, 'player_sheet_templete.csv'), 'r') as file:
                    reader = csv.reader(file)
                    rows = list(reader)

                    # Find action sections
                    try:
                        for action_num in range(1, 5):  # Assuming up to 4 actions
                            try:
                                action_start = 0
                                for i, row in enumerate(rows):
                                    if len(row) > 0 and row[0] == f"Action {action_num}":
                                        action_start = i
                                        break

                                if action_start > 0 and action_start < len(rows):
                                    # Extract action description
                                    description = ""
                                    try:
                                        if action_start + 1 < len(rows) and len(rows[action_start + 1]) > 1:
                                            description = rows[action_start + 1][1] if rows[action_start + 1][1] is not None else ""
                                    except IndexError:
                                        print(f"Warning: Error extracting description for Action {action_num}")
                                        description = ""

                                    # Extract stats and resources
                                    stats_row = 0
                                    try:
                                        for i in range(action_start, min(action_start + 10, len(rows))):  # Limit search to 10 rows
                                            if i < len(rows) and len(rows[i]) > 0 and rows[i][0] == "Stat 1":
                                                stats_row = i + 1
                                                break
                                    except IndexError:
                                        print(f"Warning: Error finding stats row for Action {action_num}")
                                        stats_row = 0

                                    if stats_row > 0 and stats_row < len(rows):
                                        try:
                                            # Safely extract and convert values with proper error handling
                                            stat1 = rows[stats_row][0] if len(rows[stats_row]) > 0 and rows[stats_row][0] is not None else None

                                            try:
                                                stat1_value = int(rows[stats_row][1]) if len(rows[stats_row]) > 1 and rows[stats_row][1] is not None and rows[stats_row][1].isdigit() else 0
                                            except (ValueError, AttributeError):
                                                stat1_value = 0

                                            stat2 = rows[stats_row][2] if len(rows[stats_row]) > 2 and rows[stats_row][2] is not None else None

                                            try:
                                                stat2_value = int(rows[stats_row][3]) if len(rows[stats_row]) > 3 and rows[stats_row][3] is not None and rows[stats_row][3].isdigit() else 0
                                            except (ValueError, AttributeError):
                                                stat2_value = 0

                                            advisor_used = True if len(rows[stats_row]) > 4 and rows[stats_row][4] is not None and rows[stats_row][4] == "Yes" else False

                                            # Collect resources used
                                            resources_used = []
                                            try:
                                                for j in range(5, 10):
                                                    if len(rows[stats_row]) > j and rows[stats_row][j] is not None and rows[stats_row][j]:
                                                        resources_used.append(rows[stats_row][j])
                                            except IndexError:
                                                print(f"Warning: Error collecting resources for Action {action_num}")

                                            try:
                                                gold_spent = int(rows[stats_row][10]) if len(rows[stats_row]) > 10 and rows[stats_row][10] is not None and rows[stats_row][10].isdigit() else 0
                                            except (ValueError, AttributeError, IndexError):
                                                gold_spent = 0

                                            cursor.execute("""
                                            INSERT INTO actions (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent)
                                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                            """, (action_num, description, stat1, stat1_value, stat2, stat2_value, advisor_used, ','.join(resources_used), gold_spent))
                                        except Exception as e:
                                            print(f"Warning: Error processing stats for Action {action_num}: {e}")
                            except Exception as e:
                                print(f"Warning: Error processing Action {action_num}: {e}")
                                continue
                    except Exception as e:
                        print(f"Warning: Error processing actions: {e}")
            except FileNotFoundError:
                print("Warning: player_sheet_templete.csv not found. Skipping actions import.")
        else:
            print(f"Actions table already has {actions_count} records. Skipping import.")

        # Check if projects table has data
        cursor.execute("SELECT COUNT(*) FROM projects")
        projects_count = cursor.fetchone()[0]

        if projects_count == 0:
            print("Importing projects data...")
            # Import projects from staff sheet
            try:
                with open(os.path.join(SCRIPT_DIR, 'default_stats.csv'), 'r') as file:
                    reader = csv.reader(file)
                    rows = list(reader)

                    # Find projects section
                    project_start = 0
                    for i, row in enumerate(rows):
                        if len(row) > 0 and "Project A" in row:
                            project_start = i
                            break

                    if project_start > 0 and project_start < len(rows):
                        try:
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
                        except (ValueError, IndexError) as e:
                            print(f"Warning: Error finding project columns: {e}")
                            # Set all columns to -1 to skip processing
                            name_col = effect_col = cost_col = resources_col = status_col = progress_col = needed_col = total_col = turn_col = -1

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
            except FileNotFoundError:
                print("Warning: default_stats.csv not found. Skipping projects import.")
        else:
            print(f"Projects table already has {projects_count} records. Skipping import.")


        # Check if standard_actions table has data
        cursor.execute("SELECT COUNT(*) FROM standard_actions")
        standard_actions_count = cursor.fetchone()[0]

        if standard_actions_count == 0:
            print("Importing standard actions (default actions) from CSV...")
            try:
                with open(os.path.join(SCRIPT_DIR, 'default_actions.csv'), 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        # Skip empty rows
                        if not row.get('Project'):
                            continue
                        project = row.get('Project', '').strip()
                        stat_type = row.get('Stat Type', '').strip()
                        points_cost = row.get('Points Cost', '').strip()
                        resource_costs = row.get('Resource Costs (total)', '').strip()
                        requirements = row.get('Requirements', '').strip()
                        benefits = row.get('Benefits', '').strip()
                        cursor.execute(
                            """
                            INSERT INTO standard_actions (project, stat_type, points_cost, resource_costs, requirements, benefits)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            (project, stat_type, points_cost, resource_costs, requirements, benefits)
                        )
            except FileNotFoundError:
                print("Warning: default_actions.csv not found. Skipping standard actions import.")
        else:
            print(f"Standard actions table already has {standard_actions_count} records. Skipping import.")

        conn.commit()
        cursor.close()
        try:
            conn.close()
        except Exception:
            pass
        _close()
        print("Data imported successfully")

    except Exception as err:
        print(f"Error: {err}")

if __name__ == "__main__":
    create_database()
    import_data()
