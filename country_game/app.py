from flask import Flask, render_template, request, redirect, url_for, flash, session
# Use ssh_db_tunnel as the sole connection method; provide a lightweight shim compatible with existing code.
from projects.country_game.country_game_utilites.ssh_db_tunnel import connect_via_tunnel as _cg_tunnel_connect
class _CGMySQLShim:
    class connector:
        Error = Exception
        @staticmethod
        def connect(*args, **kwargs):
            return _cg_tunnel_connect()
mysql = _CGMySQLShim()
import os
import re
import random
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import glob
from datetime import timedelta

# Optionally load environment variables from a local .env file for credentials
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    load_dotenv(find_dotenv(), override=False)
except Exception:
    pass

# Explicitly set template and static folders to the current project's locations
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
# Secret key: prefer environment variable; fallback to a generated key for local/dev
_app_secret = os.getenv('COUNTRY_GAME_SECRET_KEY')
if not _app_secret:
    # Generate a temporary secret if not provided (sessions will reset between restarts)
    import secrets
    _app_secret = secrets.token_urlsafe(32)
    print('Warning: COUNTRY_GAME_SECRET_KEY is not set. Using a temporary key for this run.')
app.secret_key = _app_secret

# Configure session security; allow overriding via environment for local vs production
use_secure_cookies = os.getenv('CG_SESSION_COOKIE_SECURE', 'false').lower() in ('1', 'true', 'yes')
app.config['SESSION_COOKIE_SECURE'] = use_secure_cookies  # True recommended in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('CG_SESSION_COOKIE_SAMESITE', 'Lax')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=int(os.getenv('CG_SESSION_DAYS', '1')))  # Default 1 day


# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        if not session.get('is_staff'):
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# MySQL connection parameters (loaded from environment when possible)
# Password resolution order:
#   CG_DB_PASSWORD -> MYSQL_PASSWORD -> DB_PASSWORD -> 'Darklove90!' (local dev default; see LOCAL_DB_SETUP.md)
_pwd = os.getenv('CG_DB_PASSWORD') or os.getenv('MYSQL_PASSWORD') or os.getenv('DB_PASSWORD') or 'Darklove90!'
config = {
    'user': os.getenv('CG_DB_USER', 'root'),
    'password': _pwd,
    'host': os.getenv('CG_DB_HOST', '127.0.0.1'),
    'port': int(os.getenv('CG_DB_PORT', '3306')),
    'database': os.getenv('CG_DB_NAME', 'spade605$county_game_server'),
    'raise_on_warnings': True
}

# Helpers for database naming on hosts like PythonAnywhere where DBs are namespaced as "username$dbname"
# and where CREATE DATABASE may be restricted.

def get_owner_prefix() -> str:
    """Derive the database owner prefix (e.g., 'spade605$').
    Priority: env CG_DB_OWNER_PREFIX -> prefix from config['database'] before '$' -> config['user'] + '$'
    """
    env_pref = os.getenv('CG_DB_OWNER_PREFIX')
    if env_pref:
        return env_pref if env_pref.endswith('$') else env_pref + '$'
    dbname = config.get('database') or ''
    if '$' in dbname:
        return dbname.split('$', 1)[0] + '$'
    user = config.get('user') or 'root'
    return f"{user}$"

def make_full_db_name(base: str) -> str:
    """Ensure the provided base (like 'country_test_1') has owner prefix."""
    if '$' in base:
        return base
    return f"{get_owner_prefix()}{base}"

def quote_ident(name: str) -> str:
    """Quote a MySQL identifier with backticks, escaping internal backticks if needed."""
    safe = (name or '').replace('`', '``')
    return f"`{safe}`"

def get_db_connection():
    """Get a connection to the (optionally selected) database via the unified tunnel helper."""
    try:
        conn_config = config.copy()
        if 'current_country_db' in session:
            conn_config['database'] = session['current_country_db']
        return connect_optional_tunnel(conn_config)
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def get_main_db_connection():
    """Get a connection to the main database via the unified tunnel helper."""
    try:
        conn_config = config.copy()
        main_db = os.getenv('CG_MAIN_DB_NAME', conn_config.get('database') or 'spade605$county_game_server')
        conn_config['database'] = main_db
        return connect_optional_tunnel(conn_config)
    except mysql.connector.Error as err:
        print(f"Error connecting to main MySQL database: {err}")
        return None


def connect_optional_tunnel(conn_config: dict):
    """Unified connection helper using the SSH tunnel shim (unconditionally).
    Keeps signature for backward compatibility, ignores most conn_config fields.
    """
    # Always use the tunnel-based connector for consistency and security.
    try:
        return mysql.connector.connect()
    except mysql.connector.Error as err:
        print(f"Error connecting via tunnel: {err}")
        return None


def load_standard_actions_if_empty():
    """Ensure standard_actions table is populated from default_actions.csv if empty.
    This is a safe no-op if the table already has rows or if CSV is missing.
    """
    try:
        main_conn = get_main_db_connection()
        if not main_conn:
            return
        cur = main_conn.cursor()
        try:
            # Check if table exists and count rows
            try:
                cur.execute("SELECT COUNT(*) FROM standard_actions")
            except mysql.connector.Error:
                # If the table does not exist yet, try to create it minimally
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS standard_actions (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        project VARCHAR(255) NOT NULL,
                        stat_type VARCHAR(50),
                        points_cost VARCHAR(50),
                        resource_costs TEXT,
                        requirements TEXT,
                        benefits TEXT
                    )
                    """
                )
                main_conn.commit()
                cur.execute("SELECT COUNT(*) FROM standard_actions")
            count = cur.fetchone()[0]
            if count and int(count) > 0:
                return

            # Load from CSV
            import os, csv
            # Look for default_actions.csv in several locations (new location prioritized)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            search_candidates = [
                os.path.join(script_dir, 'country_game_utilites', 'default_actions.csv'),
                os.path.join(script_dir, 'default_actions.csv'),
                os.path.join(os.getcwd(), 'projects', 'country_game', 'country_game_utilites', 'default_actions.csv'),
                os.path.join(os.getcwd(), 'projects', 'country_game', 'default_actions.csv'),
            ]
            csv_path = next((p for p in search_candidates if os.path.exists(p)), None)

            if csv_path and os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for row in reader:
                        project = (row.get('Project') or '').strip()
                        if not project:
                            continue
                        stat_type = (row.get('Stat Type') or '').strip()
                        points_cost = (row.get('Points Cost') or '').strip()
                        resource_costs = (row.get('Resource Costs (total)') or '').strip()
                        requirements = (row.get('Requirements') or '').strip()
                        benefits = (row.get('Benefits') or '').strip()
                        rows.append((project, stat_type, points_cost, resource_costs, requirements, benefits))
                    if rows:
                        cur.executemany(
                            """
                            INSERT INTO standard_actions (project, stat_type, points_cost, resource_costs, requirements, benefits)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            """,
                            rows
                        )
                        main_conn.commit()
        finally:
            cur.close()
            main_conn.close()
    except Exception as e:
        # Non-fatal; just log for debugging
        print(f"load_standard_actions_if_empty error: {e}")


def ensure_actions_is_free_column(conn):
    """Ensure the current country's actions table has the 'is_free' column.
    Adds it as BOOLEAN DEFAULT FALSE if missing. Safe to call repeatedly.
    """
    try:
        cur = conn.cursor()
        cur.execute("SHOW COLUMNS FROM actions LIKE 'is_free'")
        if not cur.fetchone():
            try:
                cur.execute("ALTER TABLE actions ADD COLUMN is_free BOOLEAN DEFAULT FALSE")
                conn.commit()
                print("Added missing 'is_free' column to actions table")
            except mysql.connector.Error as err:
                # If table doesn't exist or other error, just log
                print(f"Error adding is_free column: {err}")
        cur.close()
    except mysql.connector.Error as err:
        print(f"Error ensuring is_free column: {err}")

def get_current_country_info():
    """Get information about the currently selected country"""
    country_info = None

    # Check if a country is selected
    if 'current_country_db' in session:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # Get country info
            try:
                cursor.execute("SELECT * FROM country_info LIMIT 1")
                country_info = cursor.fetchone()

                # Add the database name to country_info
                if country_info:
                    country_info['db_name'] = session['current_country_db']
            except mysql.connector.Error as err:
                print(f"Error fetching country info: {err}")

            cursor.close()
            conn.close()

    return country_info

# Make current country info available to all templates
@app.context_processor
def inject_current_country():
    return {'current_country': get_current_country_info()}

@app.route('/')
def index():
    # Render the home page using current template and static assets
    return render_template('index.html', country_info=get_current_country_info())

# Stats routes
@app.route('/stats')
@staff_required
def stats():
    """Display all stats"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM stats")
            stats = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error fetching stats: {err}")
            stats = []
        cursor.close()
        conn.close()
        return render_template('stats.html', stats=stats)
    else:
        flash('Database connection error', 'danger')
        return render_template('stats.html', stats=[])

@app.route('/stats/add', methods=['POST'])
@staff_required
def add_stat():
    """Add a new stat"""
    if request.method == 'POST':
        name = request.form['name']
        rating = int(request.form['rating']) if request.form['rating'].strip() else 0
        modifier = request.form['modifier'] if 'modifier' in request.form else None
        notes = request.form['notes'] if 'notes' in request.form else None
        advisor = request.form['advisor'] if 'advisor' in request.form else None

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stats (name, rating, modifier, notes, advisor) VALUES (%s, %s, %s, %s, %s)",
                (name, rating, modifier, notes, advisor)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Stat added successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('stats'))

@app.route('/stats/edit/<int:id>', methods=['POST'])
@staff_required
def edit_stat(id):
    """Edit an existing stat"""
    if request.method == 'POST':
        name = request.form['name']
        rating = int(request.form['rating']) if request.form['rating'].strip() else 0
        modifier = request.form['modifier'] if 'modifier' in request.form else None
        notes = request.form['notes'] if 'notes' in request.form else None
        advisor = request.form['advisor'] if 'advisor' in request.form else None

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE stats SET name = %s, rating = %s, modifier = %s, notes = %s, advisor = %s WHERE id = %s",
                (name, rating, modifier, notes, advisor, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Stat updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('stats'))

@app.route('/stats/delete/<int:id>')
@staff_required
def delete_stat(id):
    """Delete a stat"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM stats WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Stat deleted successfully', 'success')
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('stats'))


@app.route('/stats/reset_all', methods=['POST'])
@staff_required
def reset_all_stats():
    """Set all stats ratings to 0 in the current country database."""
    conn = get_db_connection()
    if not conn:
        flash('Database connection error', 'danger')
        return redirect(url_for('stats'))
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE stats SET rating = 0")
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        conn.close()
        flash(f'Reset {affected if affected is not None else 0} stat ratings to 0.', 'success')
    except mysql.connector.Error as err:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
        flash(f'Error resetting stats: {err}', 'danger')
    return redirect(url_for('stats'))

# Resources routes
@app.route('/resources')
@login_required
def resources():
    """Display all resources"""
    # Get pre-filled name from query string if provided
    pre_filled_name = request.args.get('name', '')

    # Pre-fill type/level using DB instead of CSV when name provided
    pre_filled_type = ''
    pre_filled_tier = ''

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        if pre_filled_name:
            try:
                cursor.execute("SELECT type, COALESCE(level, tier) AS level FROM resources WHERE name = %s LIMIT 1", (pre_filled_name,))
                row = cursor.fetchone()
                if row:
                    pre_filled_type = row.get('type') or ''
                    pre_filled_tier = row.get('level') or ''
            except Exception as e:
                print(f"Error pre-filling resource details from DB: {e}")
        cursor.execute("SELECT * FROM resources")
        resources = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('resources.html', 
                              resources=resources, 
                              pre_filled_name=pre_filled_name,
                              pre_filled_type=pre_filled_type,
                              pre_filled_tier=pre_filled_tier)
    else:
        flash('Database connection error', 'danger')
        return render_template('resources.html', 
                              resources=[],
                              pre_filled_name=pre_filled_name,
                              pre_filled_type=pre_filled_type,
                              pre_filled_tier=pre_filled_tier)

@app.route('/resources/add', methods=['POST'])
@staff_required
def add_resource():
    """Add a new resource (CG5 schema)"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form.get('type')
        level = request.form.get('level')
        description = request.form.get('description')
        try:
            level_val = int(level) if level and str(level).strip() != '' else None
        except Exception:
            level_val = None

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            # Insert into CG5 columns; legacy columns remain untouched
            cursor.execute(
                "INSERT INTO resources (name, type, level, description) VALUES (%s, %s, %s, %s)",
                (name, resource_type, level_val, description)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Resource added successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('resources'))

@app.route('/resources/edit/<int:id>', methods=['POST'])
@staff_required
def edit_resource(id):
    """Edit an existing resource (CG5 schema)"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form.get('type')
        level = request.form.get('level')
        description = request.form.get('description')
        try:
            level_val = int(level) if level and str(level).strip() != '' else None
        except Exception:
            level_val = None

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE resources SET name = %s, type = %s, level = %s, description = %s WHERE id = %s",
                (name, resource_type, level_val, description, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Resource updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('resources'))

@app.route('/resources/delete/<int:id>')
@staff_required
def delete_resource(id):
    """Delete a resource"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resources WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Resource deleted successfully', 'success')
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('resources'))

@app.route('/api/resources')
@login_required
@staff_required
def api_resources():
    """Return all resources from the main database as JSON for client-side random generation.
    Fields: name, type, level, description, and tier (alias of level for compatibility).
    """
    try:
        # Use main DB so staff can pick from the canonical resource catalog
        main_conn = get_main_db_connection()
        if not main_conn:
            return {"error": "DB connection failed"}, 500
        cur = main_conn.cursor(dictionary=True)
        cur.execute("SELECT name, type, COALESCE(level, tier) AS level, description FROM resources ORDER BY name ASC")
        rows = cur.fetchall() or []
        cur.close()
        main_conn.close()
        # Add tier alias for compatibility with existing JS expectations
        for r in rows:
            r['tier'] = r.get('level')
        from flask import jsonify
        return jsonify(rows)
    except Exception as e:
        from flask import jsonify
        return jsonify({"error": str(e)}), 500


# Projects routes
@app.route('/projects')
@login_required
def projects():
    """Display all projects"""
    # Initialize containers
    projects_list = []
    stats = []
    resources = []
    player_actions = []
    all_resources = []
    players = []
    standard_actions = []

    # Load projects and in-country data
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM projects")
            projects_list = cursor.fetchall()

            # Load stats (for Player Sheet Updates)
            try:
                cursor.execute("SELECT * FROM stats")
                stats = cursor.fetchall()
            except Exception:
                pass

            # Load resources (for Player Sheet Updates)
            try:
                cursor.execute("SELECT * FROM resources")
                resources = cursor.fetchall()
            except Exception:
                pass

            # Load recent player actions (for Recent Player Actions)
            try:
                cursor.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 20")
                player_actions = cursor.fetchall()
            except Exception:
                pass
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Database connection error', 'danger')
        return render_template('projects.html', projects=[], stats=[], resources=[], player_actions=[], all_resources=[], players=[], standard_actions=[])

    # Load all resources from CSV file (for the convenience dropdown)
    try:
        import csv
        with open('country_game_utilites/default_stats.csv', 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)
            # Resources section starts around row 31
            for i in range(31, len(rows)):
                if i < len(rows) and len(rows[i]) >= 4:
                    name = rows[i][3].strip()
                    if name and name != "Name" and name != "":
                        resource_type = rows[i][4] if len(rows[i]) > 4 else ""
                        tier = rows[i][5] if len(rows[i]) > 5 else ""
                        all_resources.append({
                            'name': name,
                            'type': resource_type,
                            'tier': tier
                        })
                    # Stop when we reach the "Committed in Detail" section
                    if name == "Committed in Detail":
                        break
    except Exception as e:
        print(f"Error loading resources from CSV: {e}")

    # Load players and standard actions from the main database
    try:
        # Players
        main_conn = get_main_db_connection()
        if main_conn:
            main_cur = main_conn.cursor(dictionary=True)
            try:
                main_cur.execute("SELECT id, username, country_db FROM users WHERE role != 'staff'")
                players = main_cur.fetchall()
            finally:
                main_cur.close()
                main_conn.close()
    except Exception as e:
        print(f"Error loading players: {e}")

    try:
        load_standard_actions_if_empty()
        main_conn2 = get_main_db_connection()
        if main_conn2:
            main_cur2 = main_conn2.cursor(dictionary=True)
            try:
                main_cur2.execute("SELECT * FROM standard_actions ORDER BY stat_type, project")
                standard_actions = main_cur2.fetchall()
            finally:
                main_cur2.close()
                main_conn2.close()
    except Exception as e:
        print(f"Error loading standard actions: {e}")

    return render_template('projects.html',
                           projects=projects_list,
                           stats=stats,
                           resources=resources,
                           player_actions=player_actions,
                           all_resources=all_resources,
                           players=players,
                           standard_actions=standard_actions)

@app.route('/projects/add', methods=['POST'])
@staff_required
def add_project():
    """Add a new project"""
    if request.method == 'POST':
        name = request.form['name']
        effect = request.form['effect'] if 'effect' in request.form else None
        cost = int(request.form['cost']) if 'cost' in request.form and request.form['cost'].strip() else 0
        resources = request.form['resources'] if 'resources' in request.form else None
        status = request.form['status'] if 'status' in request.form else 'U'
        progress_per_turn = int(request.form['progress_per_turn']) if 'progress_per_turn' in request.form and request.form['progress_per_turn'].strip() else 0
        total_needed = int(request.form['total_needed']) if 'total_needed' in request.form and request.form['total_needed'].strip() else 0
        total_progress = int(request.form['total_progress']) if 'total_progress' in request.form and request.form['total_progress'].strip() else 0
        turn_started = int(request.form['turn_started']) if 'turn_started' in request.form and request.form['turn_started'].strip() else None
        winter_storage = request.form.get('winter_storage') == '1'

        # Check if it's winter and there's no winter storage project
        if not winter_storage:
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)

                    # Check if it's currently winter
                    cursor.execute("SELECT * FROM seasons WHERE current = TRUE AND name = 'Winter' LIMIT 1")
                    current_winter = cursor.fetchone()

                    if current_winter:
                        # Check if there's already a winter storage project
                        cursor.execute("SELECT COUNT(*) as count FROM projects WHERE winter_storage = TRUE")
                        winter_project_count = cursor.fetchone()['count']

                        if winter_project_count == 0:
                            flash('Warning: It is currently winter. Consider marking this as a winter food storage project or creating one.', 'warning')

                    cursor.close()
            except:
                # If seasons table doesn't exist yet, just continue
                pass

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started, winter_storage) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started, winter_storage)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Project added successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('projects'))

@app.route('/projects/edit/<int:id>', methods=['POST'])
@staff_required
def edit_project(id):
    """Edit an existing project"""
    if request.method == 'POST':
        name = request.form['name']
        effect = request.form['effect'] if 'effect' in request.form else None
        cost = int(request.form['cost']) if 'cost' in request.form and request.form['cost'].strip() else 0
        resources = request.form['resources'] if 'resources' in request.form else None
        status = request.form['status'] if 'status' in request.form else 'U'
        progress_per_turn = int(request.form['progress_per_turn']) if 'progress_per_turn' in request.form and request.form['progress_per_turn'].strip() else 0
        total_needed = int(request.form['total_needed']) if 'total_needed' in request.form and request.form['total_needed'].strip() else 0
        total_progress = int(request.form['total_progress']) if 'total_progress' in request.form and request.form['total_progress'].strip() else 0
        turn_started = int(request.form['turn_started']) if 'turn_started' in request.form and request.form['turn_started'].strip() else None
        winter_storage = request.form.get('winter_storage') == '1'

        # Check if this is the only winter storage project and it's being unmarked during winter
        if not winter_storage:
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)

                    # Check if it's currently winter
                    cursor.execute("SELECT * FROM seasons WHERE current = TRUE AND name = 'Winter' LIMIT 1")
                    current_winter = cursor.fetchone()

                    if current_winter:
                        # Check if this is the only winter storage project
                        cursor.execute("SELECT COUNT(*) as count FROM projects WHERE winter_storage = TRUE AND id != %s", (id,))
                        other_winter_projects = cursor.fetchone()['count']

                        # Check if this project was previously marked as winter storage
                        cursor.execute("SELECT winter_storage FROM projects WHERE id = %s", (id,))
                        current_project = cursor.fetchone()

                        if current_project and current_project['winter_storage'] and other_winter_projects == 0:
                            flash('Warning: This is the only winter food storage project and it is currently winter. Consider keeping it marked as a winter storage project or creating another one.', 'warning')

                    cursor.close()
            except:
                # If seasons table doesn't exist yet, just continue
                pass

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET name = %s, effect = %s, cost = %s, resources = %s, status = %s, progress_per_turn = %s, total_needed = %s, total_progress = %s, turn_started = %s, winter_storage = %s WHERE id = %s",
                (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started, winter_storage, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Project updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('projects'))

@app.route('/projects/delete/<int:id>')
@staff_required
def delete_project(id):
    """Delete a project"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Project deleted successfully', 'success')
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('projects'))

# Country routes
def get_default_countries():
    """Get a list of default countries from the generated cg5_countries.csv file"""
    countries = []
    try:
        # Resolve CSV path in new location first, then legacy, then try auto-build.
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_candidates = [
            os.path.join(script_dir, 'country_game_utilites', 'cg5_countries.csv'),
            os.path.join(script_dir, 'cg5_countries.csv'),
            os.path.join(os.getcwd(), 'projects', 'country_game', 'country_game_utilites', 'cg5_countries.csv'),
            os.path.join(os.getcwd(), 'projects', 'country_game', 'cg5_countries.csv'),
        ]
        csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)
        if not csv_path:
            # Attempt to build the CSV if missing
            try:
                from projects.country_game.country_game_utilites.descriptions_txt_to_csv import build_csv
                build_csv()
                # After build, check primary location again
                built_candidates = [
                    os.path.join(script_dir, 'country_game_utilites', 'cg5_countries.csv'),
                    os.path.join(script_dir, 'cg5_countries.csv'),
                ]
                csv_path = next((p for p in built_candidates if os.path.exists(p)), None)
            except Exception as _e:
                print(f"Could not auto-build CSV: {_e}")
        if csv_path and os.path.exists(csv_path):
            import csv as _csv
            with open(csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    name = (row.get('country_name') or '').strip()
                    if name and name not in countries:
                        countries.append(name)
            countries.sort()
            print(f"Found {len(countries)} countries in cg5_countries.csv at {csv_path}")
        else:
            raise FileNotFoundError('cg5_countries.csv not found in known locations')
    except Exception as e:
        print(f"Error getting default countries from CSV: {e}")
        # Fallback to the old method if there's an error
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            countries_dir = os.path.join(script_dir, 'countries_templates')
            country_files = glob.glob(os.path.join(countries_dir, '*.csv'))
            for fp in country_files:
                filename = os.path.basename(fp)
                country_name = filename.replace(' (Staff) - Template.csv', '')
                if country_name not in countries:
                    countries.append(country_name)
            countries.sort()
            print(f"Fallback: Found {len(country_files)} country template files")
        except Exception as inner_e:
            print(f"Error in fallback method: {inner_e}")
    return countries

@app.route('/create_country')
def create_country_form():
    """Display the country creation form only"""
    return render_template('create_country.html')


@app.route('/create_country', methods=['POST'])
def create_country():
    """Create a new country record in the central countries table (no per-country DB)."""
    if request.method == 'POST':
        # Check if a template was selected (for possible default values only)
        template_data = {}

        # Get form data
        country_name = request.form['country_name']
        ruler_name = request.form['ruler_name']
        government_type = request.form['government_type']
        description = request.form['description']

        # Get initial stats (currently unused when not creating DB; kept for future use)
        politics = int(request.form['politics'])
        military = int(request.form['military'])
        economics = int(request.form['economics'])
        culture = int(request.form['culture'])

        # Get random resources if provided (unused in registry-only creation)
        random_resources_json = request.form.get('random_resources', '')
        if random_resources_json:
            # We won't parse/use resources since no country DB is created in this mode
            pass

        # Override with template data if available (fill blanks only)
        if template_data:
            if not ruler_name and 'ruler_name' in template_data:
                ruler_name = template_data['ruler_name']
            if government_type == 'Other' and 'government_type' in template_data:
                government_type = template_data['government_type']
            if not description and 'description' in template_data:
                description = template_data['description']

        # Validate country name (allow letters, numbers, underscores and spaces for registry records)
        if not re.match(r'^[a-zA-Z0-9_ ]+$', country_name):
            flash('Country name can only contain letters, numbers, spaces, and underscores', 'danger')
            return redirect(url_for('create_country_form'))

        # Insert/Update the central countries registry (no database is created here)
        ok = False
        try:
            ok = add_country_registry_entry(
                name=country_name,
                ruler_name=ruler_name or f"Ruler of {country_name}",
                government_type=government_type or 'Other',
                description=description or '',
                db_name=None,  # no per-country DB
                is_open_for_selection=True,
                assigned_player_id=None,
                politics=politics,
                military=military,
                economics=economics,
                culture=culture,
                resources_json=random_resources_json
            )
        except Exception as e:
            print(f"Error adding registry entry: {e}")
            ok = False

        if ok:
            flash(f'Country {country_name} added to registry successfully (no database created).', 'success')
            return redirect(url_for('create_country_form'))
        else:
            flash('Failed to add country to registry', 'danger')
            return redirect(url_for('create_country_form'))


def add_country_registry_entry(name, ruler_name, government_type, description, db_name,
                               is_open_for_selection=True, assigned_player_id=None,
                               politics=None, military=None, economics=None, culture=None,
                               resources_json=None):
    """Insert or update a row in the central countries table in the main DB, including initial stats/resources."""
    try:
        main_conn = get_main_db_connection()
        if not main_conn:
            return False
        cur = main_conn.cursor()
        # Ensure table exists (safety; main setup should create it)
        cur.execute(
            """
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
            """
        )
        cur.execute(
            """
            INSERT INTO countries (name, ruler_name, government_type, description, db_name, assigned_player_id, is_open_for_selection,
                                   politics, military, economics, culture, resources_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                ruler_name=VALUES(ruler_name),
                government_type=VALUES(government_type),
                description=VALUES(description),
                db_name=COALESCE(VALUES(db_name), db_name),
                assigned_player_id=COALESCE(VALUES(assigned_player_id), assigned_player_id),
                is_open_for_selection=COALESCE(VALUES(is_open_for_selection), is_open_for_selection),
                politics=COALESCE(VALUES(politics), politics),
                military=COALESCE(VALUES(military), military),
                economics=COALESCE(VALUES(economics), economics),
                culture=COALESCE(VALUES(culture), culture),
                resources_json=COALESCE(VALUES(resources_json), resources_json)
            """,
            (name, ruler_name, government_type, description, db_name, assigned_player_id, 1 if is_open_for_selection else 0,
             politics, military, economics, culture, resources_json)
        )
        main_conn.commit()
        cur.close()
        main_conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Error writing to countries table: {err}")
        try:
            cur.close()
            main_conn.close()
        except Exception:
            pass
        return False




@app.route('/countries')
@login_required
@staff_required
def list_countries():
    """List all countries from the central registry (countries table)"""
    countries = []
    try:
        main_conn = get_main_db_connection()
        if not main_conn:
            raise mysql.connector.Error("Failed to connect to main DB")
        cur = main_conn.cursor(dictionary=True)
        # Ensure table exists (safety)
        cur.execute(
            """
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
            """
        )
        cur.execute(
            """
            SELECT name, ruler_name, government_type, description, db_name, is_open_for_selection
              FROM countries
             WHERE COALESCE(db_name, '') <> ''
          ORDER BY name ASC
            """
        )
        rows = cur.fetchall() or []
        for r in rows:
            countries.append({
                'name': r.get('name'),
                'ruler_name': r.get('ruler_name'),
                'government_type': r.get('government_type'),
                'description': r.get('description') or '',
                'db_name': r.get('db_name') or '',
                'is_open_for_selection': bool(r.get('is_open_for_selection')) if r.get('is_open_for_selection') is not None else True,
            })
        cur.close()
        main_conn.close()
    except mysql.connector.Error as err:
        print(f"Error listing countries from registry: {err}")
    return render_template('select_country.html', countries=countries)

@app.route('/select_country/<db_name>')
@login_required
@staff_required
def select_country(db_name):
    """Select a country database"""
    try:
        # Normalize to full owner-prefixed DB name
        full_name = make_full_db_name(db_name)

        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = connect_optional_tunnel(conn_config)
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute("SHOW DATABASES LIKE %s", (full_name,))
        if cursor.fetchone():
            # Set the current country database in session
            session['current_country_db'] = full_name
            flash(f'Switched to country database: {full_name}', 'success')
        else:
            flash(f'Country database not found: {full_name}', 'danger')

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Error selecting country database: {err}")
        flash(f'Error selecting country database: {err}', 'danger')

    return redirect(url_for('index'))

@app.route('/clear_country')
def clear_country():
    """Clear the current country selection"""
    if 'current_country_db' in session:
        del session['current_country_db']
        flash('Country selection cleared', 'success')
    return redirect(url_for('index'))

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect to the database
        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user and check_password_hash(user['password'], password):
                # Check if user has a country assigned (only for non-staff users)
                if user['role'] != 'staff' and (not user.get('country_db')):
                    # Store user ID for message
                    user_id = user['id']

                    # Send message to staff
                    try:
                        # Reopen connection to send message
                        conn = get_main_db_connection()
                        cursor = conn.cursor(dictionary=True)

                        # Find a staff user to send the message to
                        cursor.execute("SELECT id FROM users WHERE role = 'staff' LIMIT 1")
                        staff = cursor.fetchone()

                        if staff:
                            # Send message to staff
                            cursor.execute(
                                "INSERT INTO messages (sender_id, recipient_id, subject, content) VALUES (%s, %s, %s, %s)",
                                (user_id, staff['id'], 'Login without country', f"User {username} tried to log in but has no country assigned.")
                            )
                            conn.commit()

                        cursor.close()
                        conn.close()
                    except mysql.connector.Error as err:
                        print(f"Error sending message to staff: {err}")

                    flash('You do not have a country assigned. Please contact staff.', 'danger')
                    return redirect(url_for('login'))

                # Make session permanent so it persists across tabs and browser sessions
                session.permanent = True
                session['username'] = user['username']
                session['user_id'] = user['id']
                session['is_staff'] = (user['role'] == 'staff')

                # Set current country database in session if user has one assigned
                if not session['is_staff'] and user.get('country_db'):
                    session['current_country_db'] = user.get('country_db')

                flash(f'Welcome, {username}!', 'success')

                # Redirect staff users to staff dashboard, regular users to player dashboard
                if session['is_staff']:
                    return redirect(url_for('staff_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'danger')
        else:
            flash('Database connection error', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('username', None)
    session.pop('user_id', None)
    session.pop('is_staff', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/rules')
def rules():
    """Display game rules from docstrings in the game_rules module"""
    try:
        # Import the game_rules module
        from projects.country_game.country_game_utilites.game_rules import get_all_sections, get_suggestions

        # Get sections and suggestions from the module
        sections = get_all_sections()
        suggestions = get_suggestions()

    except Exception as e:
        flash(f'Error loading game rules: {str(e)}', 'danger')
        sections = {}
        suggestions = []

    return render_template('rules.html', sections=sections, suggestions=suggestions)

@app.route('/country_descriptions')
def country_descriptions():
    """Display country descriptions from CG5_Country_Descriptions.txt"""
    try:
        # Read the country descriptions file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'CG5_Country_Descriptions.txt')

        with open(file_path, 'r') as file:
            content = file.readlines()

        # Parse the content into a structured format
        descriptions = []
        current_description = None
        seen_countries = set()  # To track and prevent duplicate countries

        for line in content:
            line = line.strip()
            if not line:
                continue

            # Check if this is a country entry (starts with a number followed by a period)
            if re.match(r'^\d+\.', line):
                # Extract country information
                parts = line.split(' - ')
                if len(parts) >= 3:
                    country_info = parts[0].split(' ', 1)
                    country_number = country_info[0].rstrip('.')
                    country_name = country_info[1]

                    # Skip if we've already seen this country
                    if country_name in seen_countries:
                        current_description = None
                        continue

                    seen_countries.add(country_name)
                    alignment = parts[1]

                    # The government type might contain additional hyphens
                    government_type = ' - '.join(parts[2:-1]) if len(parts) > 3 else parts[2]

                    # The description is the last part
                    description = parts[-1] if len(parts) > 3 else ""

                    current_description = {
                        'number': country_number,
                        'name': country_name,
                        'alignment': alignment,
                        'government_type': government_type,
                        'description': description,
                        'player_assigned': None  # Initialize player assignment as None
                    }
                    descriptions.append(current_description)
            elif current_description and not line.startswith('There are'):
                # Append to the description of the current country
                if current_description['description']:
                    current_description['description'] += ' ' + line
                else:
                    current_description['description'] = line

        # Renumber countries sequentially
        for i, desc in enumerate(descriptions, 1):
            desc['number'] = str(i)

        # Fetch player assignments from the database
        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT u.username, u.country_db 
                FROM users u 
                WHERE u.country_db IS NOT NULL
            """)
            player_assignments = cursor.fetchall()
            cursor.close()
            conn.close()

            # Map country_db to player username
            country_assignments = {}
            for assignment in player_assignments:
                if assignment['country_db']:
                    # Extract country name from the database name (e.g., "country_game_karis" -> "Karis")
                    country_name = assignment['country_db'].replace('country_game_', '').title()
                    country_assignments[country_name] = assignment['username']

            # Update descriptions with player assignments
            for desc in descriptions:
                if desc['name'] in country_assignments:
                    desc['player_assigned'] = country_assignments[desc['name']]

        # Define alignment code to full name mapping
        alignment_mapping = {
            'LG': 'Lawful Good',
            'NG': 'Neutral Good',
            'CG': 'Chaotic Good',
            'LN': 'Lawful Neutral',
            'N': 'True Neutral',
            'CN': 'Chaotic Neutral',
            'LE': 'Lawful Evil',
            'NE': 'Neutral Evil',
            'CE': 'Chaotic Evil'
        }

        # Get unique alignments and government types for filtering
        alignments = sorted(list(set(desc['alignment'] for desc in descriptions)))
        government_types = sorted(list(set(desc['government_type'] for desc in descriptions)))

    except Exception as e:
        flash(f'Error loading country descriptions: {str(e)}', 'danger')
        descriptions = []
        alignments = []
        government_types = []

    return render_template('country_descriptions.html', 
                          descriptions=descriptions, 
                          map_image='CG5_basic_map.png',
                          alignments=alignments,
                          government_types=government_types,
                          alignment_mapping=alignment_mapping)






@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        role = request.form['role']

        # Validate input
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        # Only allow staff to create staff accounts
        if role == 'staff' and not session.get('is_staff'):
            flash('You do not have permission to create staff accounts', 'danger')
            return render_template('register.html')

        # Connect to the database
        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor()

            # Check if username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash('Username already exists', 'danger')
                return render_template('register.html')

            # Hash the password
            hashed_password = generate_password_hash(password)

            # Insert new user
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_password, role)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Database connection error', 'danger')

    return render_template('register.html')

# User management routes
@app.route('/users')
@staff_required
def users():
    """Display all users"""
    conn = get_main_db_connection()
    users = []
    countries = []

    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # Get countries from central registry instead of scanning per-country DBs
        try:
            main_conn = get_main_db_connection()
            if not main_conn:
                raise mysql.connector.Error("Failed to connect to main DB for countries list")
            cur2 = main_conn.cursor(dictionary=True)
            cur2.execute("SELECT name, db_name FROM countries ORDER BY name ASC")
            rows = cur2.fetchall() or []
            countries = [{'name': r.get('name'), 'db_name': r.get('db_name') or ''} for r in rows if r.get('db_name')]
            cur2.close()
            main_conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching countries registry: {err}")

        cursor.close()
        conn.close()
        return render_template('users.html', users=users, countries=countries)
    else:
        flash('Database connection error', 'danger')
        return render_template('users.html', users=[], countries=[])

@app.route('/users/add', methods=['POST'])
@staff_required
def add_user():
    """Add a new user"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        country_db = request.form['country_db'] if 'country_db' in request.form else None

        # Validate input
        if not username or not password:
            flash('Username and password are required', 'danger')
            return redirect(url_for('users'))

        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor()

            # Check if country_db column exists, add it if it doesn't
            try:
                cursor.execute("SHOW COLUMNS FROM users LIKE 'country_db'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN country_db VARCHAR(100)")
                    conn.commit()
                    print("Added missing country_db column to users table")
            except mysql.connector.Error as err:
                print(f"Error checking/adding country_db column: {err}")

            # Check if username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash('Username already exists', 'danger')
                return redirect(url_for('users'))

            # Hash the password
            hashed_password = generate_password_hash(password)

            # Insert new user
            cursor.execute(
                "INSERT INTO users (username, password, role, country_db) VALUES (%s, %s, %s, %s)",
                (username, hashed_password, role, country_db)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash('User added successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('users'))

@app.route('/users/edit/<int:id>', methods=['POST'])
@staff_required
def edit_user(id):
    """Edit an existing user"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        country_db = request.form['country_db'] if 'country_db' in request.form else None

        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor()

            # Check if country_db column exists, add it if it doesn't
            try:
                cursor.execute("SHOW COLUMNS FROM users LIKE 'country_db'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN country_db VARCHAR(100)")
                    conn.commit()
                    print("Added missing country_db column to users table")
            except mysql.connector.Error as err:
                print(f"Error checking/adding country_db column: {err}")

            # Check if username already exists (for a different user)
            cursor.execute("SELECT * FROM users WHERE username = %s AND id != %s", (username, id))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                flash('Username already exists', 'danger')
                return redirect(url_for('users'))

            # Update user
            if password:
                # If password is provided, update it too
                hashed_password = generate_password_hash(password)
                cursor.execute(
                    "UPDATE users SET username = %s, password = %s, role = %s, country_db = %s WHERE id = %s",
                    (username, hashed_password, role, country_db, id)
                )
            else:
                # Otherwise, just update username, role, and country
                cursor.execute(
                    "UPDATE users SET username = %s, role = %s, country_db = %s WHERE id = %s",
                    (username, role, country_db, id)
                )

            conn.commit()
            cursor.close()
            conn.close()

            flash('User updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('users'))

@app.route('/users/delete/<int:id>')
@staff_required
def delete_user(id):
    """Delete a user"""
    # Don't allow deleting yourself
    if session.get('user_id') == id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('users'))

    conn = get_main_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('User deleted successfully', 'success')
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('users'))

# Player routes
# Removed player_dashboard route and associated view per deprecation of player dashboard UI.


# Messaging routes
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    """Send a message to another user"""
    if request.method == 'POST':
        sender_id = session.get('user_id')
        subject = request.form['subject']
        content = request.form['content']

        # Determine recipient based on user role
        if session.get('is_staff'):
            # Staff sending to a specific player
            recipient_id = int(request.form['recipient_id'])
        else:
            # Player sending to staff (get first staff user)
            conn = get_main_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE role = 'staff' LIMIT 1")
            staff = cursor.fetchone()
            cursor.close()
            conn.close()

            if staff:
                recipient_id = staff['id']
            else:
                flash('No staff members available to receive messages', 'danger')
                return redirect(url_for('index' if not session.get('is_staff') else 'staff_dashboard'))

        # Insert the message
        try:
            conn = get_main_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO messages (sender_id, recipient_id, subject, content) VALUES (%s, %s, %s, %s)",
                        (sender_id, recipient_id, subject, content)
                    )
                    conn.commit()
                    flash('Message sent successfully', 'success')
                except mysql.connector.Error as err:
                    print(f"Error sending message: {err}")
                    flash('Error sending message. The messaging system may not be set up yet.', 'danger')
                finally:
                    cursor.close()
                    conn.close()
            else:
                flash('Database connection error', 'danger')
        except Exception as e:
            print(f"Unexpected error in send_message: {e}")
            flash('An unexpected error occurred', 'danger')

        # Redirect based on user role
        if session.get('is_staff'):
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('index'))

# Staff routes
@app.route('/import_countries_registry')
@staff_required
def import_countries_registry():
    """Import or update entries in the central countries registry from cg5_countries.csv without creating DBs."""
    try:
        # Ensure CSV exists; try to build if missing
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = None
        candidates = [
            os.path.join(script_dir, 'country_game_utilites', 'cg5_countries.csv'),
            os.path.join(script_dir, 'cg5_countries.csv'),
            os.path.join(os.getcwd(), 'projects', 'country_game', 'country_game_utilites', 'cg5_countries.csv'),
        ]
        for p in candidates:
            if os.path.exists(p):
                csv_path = p
                break
        if not csv_path:
            try:
                from projects.country_game.country_game_utilites.descriptions_txt_to_csv import build_csv
                build_csv()
            except Exception as _e:
                print(f"Could not auto-build CSV for registry import: {_e}")
        import csv as _csv
        if not csv_path or not os.path.exists(csv_path):
            flash('Country descriptions CSV not found and could not be auto-built.', 'danger')
            return redirect(url_for('create_country_form'))

        # Read CSV and upsert into countries registry
        imported = 0
        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = _csv.DictReader(f)
            for row in reader:
                name = (row.get('country_name') or '').strip()
                if not name:
                    continue
                gov = (row.get('government_description') or '').strip()
                desc = (row.get('description') or '').strip()
                # Use placeholder ruler until set later
                ok = add_country_registry_entry(name=name,
                                                ruler_name=f"Ruler of {name}" if gov else 'TBD',
                                                government_type=gov or 'Other',
                                                description=desc,
                                                db_name=None,
                                                is_open_for_selection=True,
                                                assigned_player_id=None)
                if ok:
                    imported += 1
        flash(f'Registry import complete. Upserted {imported} rows from CSV.', 'success')
    except Exception as e:
        flash(f'Error importing registry from CSV: {e}', 'danger')
    return redirect(url_for('create_country_form'))

@app.route('/create_countries_from_descriptions')
@staff_required
def create_countries_from_descriptions():
    """Import/Upsert countries into the central registry from cg5_countries.csv (no DB creation)."""
    try:
        # Load countries from CSV (auto-build if missing)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = None
        candidates = [
            os.path.join(script_dir, 'country_game_utilites', 'cg5_countries.csv'),
            os.path.join(script_dir, 'cg5_countries.csv'),
            os.path.join(os.getcwd(), 'projects', 'country_game', 'country_game_utilites', 'cg5_countries.csv'),
        ]
        for p in candidates:
            if os.path.exists(p):
                csv_path = p
                break
        if not csv_path:
            try:
                from projects.country_game.country_game_utilites.descriptions_txt_to_csv import build_csv
                build_csv()
            except Exception as _e:
                print(f"Could not auto-build CSV: {_e}")
        import csv as _csv
        if not csv_path or not os.path.exists(csv_path):
            flash('Country descriptions CSV not found and could not be auto-built.', 'danger')
            return redirect(url_for('create_country_form'))

        upserted = 0
        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = _csv.DictReader(f)
            for row in reader:
                name = (row.get('country_name') or '').strip()
                if not name:
                    continue
                gov = (row.get('government_description') or '').strip() or 'Other'
                desc = (row.get('description') or '').strip()

                # Generate Initial Stats (1-3)
                politics = random.randint(1, 3)
                military = random.randint(1, 3)
                economics = random.randint(1, 3)
                culture = random.randint(1, 3)

                # Generate Initial Resources (5-12 random items)
                all_resources = [
                    { "name": "Iron", "type": "Metal", "tier": 1 },
                    { "name": "Copper", "type": "Metal", "tier": 1 },
                    { "name": "Gold", "type": "Precious Metal", "tier": 2 },
                    { "name": "Silver", "type": "Precious Metal", "tier": 2 },
                    { "name": "Wheat", "type": "Food", "tier": 1 },
                    { "name": "Rice", "type": "Food", "tier": 1 },
                    { "name": "Cattle", "type": "Livestock", "tier": 1 },
                    { "name": "Horses", "type": "Livestock", "tier": 2 },
                    { "name": "Timber", "type": "Wood", "tier": 1 },
                    { "name": "Exotic Wood", "type": "Wood", "tier": 2 },
                    { "name": "Coal", "type": "Fuel", "tier": 1 },
                    { "name": "Oil", "type": "Fuel", "tier": 2 },
                    { "name": "Gems", "type": "Luxury", "tier": 3 },
                    { "name": "Spices", "type": "Luxury", "tier": 2 },
                    { "name": "Wine", "type": "Luxury", "tier": 2 },
                    { "name": "Silk", "type": "Textile", "tier": 2 },
                    { "name": "Cotton", "type": "Textile", "tier": 1 },
                    { "name": "Stone", "type": "Building Material", "tier": 1 },
                    { "name": "Marble", "type": "Building Material", "tier": 2 },
                    { "name": "Fish", "type": "Food", "tier": 1 }
                ]
                num_resources = random.randint(5, 12)
                shuffled = list(all_resources)
                random.shuffle(shuffled)
                selected = shuffled[:num_resources]
                for res in selected:
                    res["natively_produced"] = random.randint(1, 3)
                    res["trade"] = random.randint(0, 1)
                import json as _json
                resources_json = _json.dumps(selected)

                if add_country_registry_entry(name=name,
                                              ruler_name=f"Ruler of {name}",
                                              government_type=gov,
                                              description=desc,
                                              db_name=None,
                                              is_open_for_selection=True,
                                              assigned_player_id=None,
                                              politics=politics, military=military, economics=economics, culture=culture,
                                              resources_json=resources_json):
                    upserted += 1
        flash(f'Registry update complete. Upserted {upserted} countries from descriptions CSV. No databases were created.', 'success')
        return redirect(url_for('create_country_form'))
    except Exception as e:
        flash(f'Error importing countries from descriptions: {str(e)}', 'danger')
        return redirect(url_for('create_country_form'))

@app.route('/create_starting_countries')
@staff_required
def create_starting_countries():
    """Upsert starting countries into the central registry based on default countries (no DB creation)."""
    try:
        default_countries = get_default_countries()
        upserted = 0
        for country_name in default_countries:
            if not country_name:
                continue
            ok = add_country_registry_entry(
                name=country_name,
                ruler_name=f"Ruler of {country_name}",
                government_type='Default',
                description=f"Starting country based on {country_name}",
                db_name=None,
                is_open_for_selection=True,
                assigned_player_id=None,
            )
            if ok:
                upserted += 1
        if upserted > 0:
            flash(f'Upserted {upserted} starting countries into registry (no databases created).', 'success')
        else:
            flash('No starting countries were upserted. They may already exist in the registry.', 'info')
        return redirect(url_for('create_country_form'))
    except Exception as e:
        flash(f'Error upserting starting countries: {str(e)}', 'danger')
        return redirect(url_for('create_country_form'))

@app.route('/delete_starting_countries')
@staff_required
def delete_starting_countries():
    """Delete all starting countries"""
    try:
        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = connect_optional_tunnel(conn_config)
        cursor = conn.cursor(dictionary=True)

        # Get all databases that start with owner-prefixed 'country_starting_'
        pattern = make_full_db_name('country_starting_%')
        cursor.execute("SHOW DATABASES LIKE %s", (pattern,))
        starting_country_dbs = [list(db.values())[0] for db in cursor.fetchall()]

        # Track how many countries were deleted
        deleted_count = 0

        # Delete each starting country
        for db_name in starting_country_dbs:
            # Drop the database
            cursor.execute(f"DROP DATABASE {quote_ident(db_name)}")

            # If this was the current country, clear the selection
            if session.get('current_country_db') == db_name:
                session.pop('current_country_db', None)

            deleted_count += 1

        cursor.close()
        conn.close()

        if deleted_count > 0:
            flash(f'Successfully deleted {deleted_count} starting countries', 'success')
        else:
            flash('No starting countries were found to delete', 'info')

        return redirect(url_for('create_country_form'))

    except mysql.connector.Error as err:
        print(f"Error deleting starting countries: {err}")
        flash(f'Error deleting starting countries: {err}', 'danger')
        return redirect(url_for('create_country_form'))

@app.route('/staff_dashboard')
@staff_required
def staff_dashboard():
    """Staff dashboard for country management and player interactions"""
    countries = []
    players = []
    stats = []
    resources = []
    all_resources = []  # List of all resources from CSV
    messages = []
    player_actions = []
    standard_actions = []

    # Get CPU quota info from PythonAnywhere API
    cpu_quota_info = None
    try:
        import requests
        username = 'spade605'
        token = 'ba0f3dd3208247412bfe2457bda6a756616e852d'

        response = requests.get(
            'https://www.pythonanywhere.com/api/v0/user/{username}/cpu/'.format(
                username=username
            ),
            headers={'Authorization': 'Token {token}'.format(token=token)}
        )
        if response.status_code == 200:
            cpu_quota_info = response.json()
        else:
            print('Got unexpected status code {}: {!r}'.format(response.status_code, response.content))
    except Exception as e:
        print(f"Error fetching CPU quota info: {e}")

    try:
        # Connect to MySQL server for user data
        conn = get_main_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all non-staff users (players)
        cursor.execute("SELECT id, username, country_db FROM users WHERE role != 'staff'")
        players = cursor.fetchall()

        # Create a list of players with their assigned countries
        players_with_countries = []
        for player in players:
            player_info = {
                'id': player['id'],
                'username': player['username'],
                'country_db': player['country_db'],
                'country_name': None
            }
            players_with_countries.append(player_info)

        # Get messages for this staff member
        try:
            user_id = session.get('user_id')
            cursor.execute("""
                SELECT m.*, 
                       sender.username as sender_username, 
                       recipient.username as recipient_username 
                FROM messages m
                JOIN users sender ON m.sender_id = sender.id
                JOIN users recipient ON m.recipient_id = recipient.id
                WHERE m.sender_id = %s OR m.recipient_id = %s
                ORDER BY m.created_at DESC
            """, (user_id, user_id))
            messages = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error fetching messages for staff: {err}")
            # If there's an error (like table doesn't exist), just continue with empty messages list

        cursor.close()
        conn.close()

        # Ensure standard actions exist, then load them from the main database
        try:
            load_standard_actions_if_empty()
            main_conn2 = get_main_db_connection()
            if main_conn2:
                main_cur2 = main_conn2.cursor(dictionary=True)
                try:
                    main_cur2.execute("SELECT * FROM standard_actions ORDER BY stat_type, project")
                    standard_actions = main_cur2.fetchall()
                except mysql.connector.Error as err:
                    print(f"Error fetching standard actions: {err}")
                finally:
                    main_cur2.close()
                    main_conn2.close()
        except Exception as e:
            print(f"Error loading standard actions: {e}")

        # Connect to country database for game data
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # Get stats
            cursor.execute("SELECT * FROM stats")
            stats = cursor.fetchall()

            # Get resources
            cursor.execute("SELECT * FROM resources")
            resources = cursor.fetchall()

            # Get player actions
            cursor.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 20")
            player_actions = cursor.fetchall()

            cursor.close()
            conn.close()

        # Load all resources from CSV file
        try:
            import csv
            with open('country_game_utilites/default_stats.csv', 'r') as file:
                reader = csv.reader(file)
                rows = list(reader)

                # Find resources section (starting at row 31)
                for i in range(31, len(rows)):
                    if i < len(rows) and len(rows[i]) >= 4:
                        name = rows[i][3].strip()
                        # Process rows with resource names
                        if name and name != "Name" and name != "":
                            resource_type = rows[i][4] if len(rows[i]) > 4 else ""
                            tier = rows[i][5] if len(rows[i]) > 5 else ""

                            # Add to all_resources list
                            all_resources.append({
                                'name': name,
                                'type': resource_type,
                                'tier': tier
                            })

                        # Stop when we reach the "Committed in Detail" section
                        if name == "Committed in Detail":
                            break
        except Exception as e:
            print(f"Error loading resources from CSV: {e}")

        # Build countries list from central registry instead of scanning DBs
        try:
            main_conn = get_main_db_connection()
            if main_conn:
                main_cur = main_conn.cursor(dictionary=True)
                # Ensure table exists (safety)
                main_cur.execute(
                    """
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
                    """
                )
                # Fetch countries with optional assigned player
                main_cur.execute(
                    """
                    SELECT c.*, u.id AS player_id, u.username AS player_username
                      FROM countries c
                 LEFT JOIN users u ON u.id = c.assigned_player_id
                  ORDER BY c.name ASC
                    """
                )
                rows = main_cur.fetchall() or []
                countries.clear()
                for r in rows:
                    # Only include countries with a concrete database in the staff dropdown list
                    if not r.get('db_name'):
                        continue
                    countries.append({
                        'name': r.get('name'),
                        'ruler_name': r.get('ruler_name'),
                        'government_type': r.get('government_type'),
                        'description': r.get('description') or '',
                        'db_name': r.get('db_name') or '',
                        'assigned_player': ({'id': r.get('player_id'), 'username': r.get('player_username')} if r.get('player_id') else None),
                        'is_open_for_selection': (bool(r.get('is_open_for_selection')) if r.get('is_open_for_selection') is not None else True),
                    })
                # Update players_with_countries list with country names and religions
                # Map db_name to country name for quick lookup
                db_to_name = {c['db_name']: c['name'] for c in countries if c['db_name']}
                for player_info in players_with_countries:
                    if player_info['country_db'] and player_info['country_db'] in db_to_name:
                        player_info['country_name'] = db_to_name[player_info['country_db']]
                main_cur.close()
                main_conn.close()
        except mysql.connector.Error as err:
            print(f"Error fetching countries for staff dashboard: {err}")

    except mysql.connector.Error as err:
        print(f"Error preparing staff dashboard: {err}")
        flash(f'Error preparing staff dashboard: {err}', 'danger')


    return render_template('staff_dashboard.html', 
                         countries=countries,
                         players=players,
                         players_with_countries=players_with_countries,
                         stats=stats,
                         resources=resources,
                         all_resources=all_resources,
                         messages=messages,
                         player_actions=player_actions,
                         cpu_quota_info=cpu_quota_info,
                         standard_actions=standard_actions)

@app.route('/delete_country/<db_name>')
@staff_required
def delete_country(db_name):
    """Delete a country database"""
    try:
        # Normalize and validate database name
        full_name = make_full_db_name(db_name)
        base = full_name.split('$', 1)[-1]
        if not base.startswith('country_'):
            flash('Invalid country database name', 'danger')
            return redirect(url_for('staff_dashboard'))

        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = connect_optional_tunnel(conn_config)
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute("SHOW DATABASES LIKE %s", (full_name,))
        if cursor.fetchone():
            # Drop the database
            cursor.execute(f"DROP DATABASE {quote_ident(full_name)}")
            flash(f'Country database {full_name} has been deleted', 'success')

            # If this was the current country, clear the selection
            if session.get('current_country_db') == full_name:
                session.pop('current_country_db', None)
        else:
            flash(f'Country database not found: {full_name}', 'danger')

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Error deleting country database: {err}")
        flash(f'Error deleting country database: {err}', 'danger')

    return redirect(url_for('staff_dashboard'))

@app.route('/update_player_stats', methods=['POST'])
@staff_required
def update_player_stats():
    """Update a player's stat from the staff dashboard"""
    if request.method == 'POST':
        stat_id = int(request.form['stat_id'])
        new_rating = int(request.form['new_rating'])
        notes = request.form['notes'] if 'notes' in request.form else None

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # First get the current stat to preserve other fields
            cursor.execute("SELECT * FROM stats WHERE id = %s", (stat_id,))
            stat = cursor.fetchone()

            if stat:
                # Update the rating and notes
                cursor.execute(
                    "UPDATE stats SET rating = %s, notes = %s WHERE id = %s",
                    (new_rating, notes, stat_id)
                )
                conn.commit()
                flash('Stat updated successfully', 'success')
            else:
                flash('Stat not found', 'danger')

            cursor.close()
            conn.close()
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('staff_dashboard'))

@app.route('/update_player_resources', methods=['POST'])
@staff_required
def update_player_resources():
    """Update a player's resource from the staff dashboard"""
    if request.method == 'POST':
        resource_id = int(request.form['resource_id'])
        field_to_update = request.form['field_to_update']
        new_value = int(request.form['new_value'])

        # Validate field_to_update to prevent SQL injection
        valid_fields = ['natively_produced', 'trade', 'committed', 'not_developed', 'available']
        if field_to_update not in valid_fields:
            flash('Invalid field specified', 'danger')
            return redirect(url_for('staff_dashboard'))

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # Update the specified field
            query = f"UPDATE resources SET {field_to_update} = %s WHERE id = %s"
            cursor.execute(query, (new_value, resource_id))
            conn.commit()

            flash('Resource updated successfully', 'success')
            cursor.close()
            conn.close()
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('staff_dashboard'))

@app.route('/assign_country_to_player', methods=['POST'])
@staff_required
def assign_country_to_player():
    """Assign a country to a player"""
    if request.method == 'POST':
        player_id = request.form['player_id']
        country_db = request.form['country_db']

        conn = get_main_db_connection()
        if conn:
            cursor = conn.cursor()

            # Check if country_db column exists, add it if it doesn't
            try:
                cursor.execute("SHOW COLUMNS FROM users LIKE 'country_db'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN country_db VARCHAR(100)")
                    conn.commit()
                    print("Added missing country_db column to users table")
            except mysql.connector.Error as err:
                print(f"Error checking/adding country_db column: {err}")

            # Update the user's country_db field
            cursor.execute(
                "UPDATE users SET country_db = %s WHERE id = %s",
                (country_db, player_id)
            )
            conn.commit()

            # Also reflect assignment in central countries table: set assigned_player_id and close selection
            try:
                cursor.execute(
                    "UPDATE countries SET assigned_player_id = %s, is_open_for_selection = FALSE WHERE db_name = %s",
                    (player_id, country_db)
                )
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Error updating countries registry on assignment: {err}")

            # Get the player's username for the flash message
            cursor.execute("SELECT username FROM users WHERE id = %s", (player_id,))
            player = cursor.fetchone()
            player_username = player[0] if player else "Unknown"

            # Get the country name for the flash message
            country_name = "No Country"
            if country_db:
                # Connect to the country database to get its name
                try:
                    conn_config = config.copy()
                    if 'database' in conn_config:
                        del conn_config['database']

                    conn2 = mysql.connector.connect(**conn_config)
                    cursor2 = conn2.cursor(dictionary=True)

                    cursor2.execute(f"USE {country_db}")
                    cursor2.execute("SELECT name FROM country_info LIMIT 1")
                    country_data = cursor2.fetchone()

                    if country_data:
                        country_name = country_data['name']

                    cursor2.close()
                    conn2.close()
                except mysql.connector.Error as err:
                    print(f"Error getting country name: {err}")

            cursor.close()
            conn.close()

            if country_db:
                flash(f'Country "{country_name}" assigned to player "{player_username}" successfully', 'success')
            else:
                flash(f'Country assignment removed from player "{player_username}" successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('staff_dashboard'))

@app.route('/remove_player_from_country/<int:player_id>', methods=['GET'])
@staff_required
def remove_player_from_country(player_id):
    """Remove a player from a country"""
    conn = get_main_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        # Get the player's current country for the flash message
        cursor.execute("SELECT username, country_db FROM users WHERE id = %s", (player_id,))
        player = cursor.fetchone()

        if player and player['country_db']:
            player_username = player['username']
            country_db = player['country_db']

            # Get the country name for the flash message
            country_name = "Unknown Country"
            try:
                conn_config = config.copy()
                if 'database' in conn_config:
                    del conn_config['database']

                conn2 = mysql.connector.connect(**conn_config)
                cursor2 = conn2.cursor(dictionary=True)

                cursor2.execute(f"USE {country_db}")
                cursor2.execute("SELECT name FROM country_info LIMIT 1")
                country_data = cursor2.fetchone()

                if country_data:
                    country_name = country_data['name']

                cursor2.close()
                conn2.close()
            except mysql.connector.Error as err:
                print(f"Error getting country name: {err}")

            # Update the user's country_db field to empty string
            cursor.execute(
                "UPDATE users SET country_db = '' WHERE id = %s",
                (player_id,)
            )
            conn.commit()

            # Mark country as available again in countries registry
            try:
                cursor.execute(
                    "UPDATE countries SET assigned_player_id = NULL, is_open_for_selection = TRUE WHERE db_name = %s",
                    (country_db,)
                )
                conn.commit()
            except mysql.connector.Error as err:
                print(f"Error updating countries registry on removal: {err}")

            flash(f'Player "{player_username}" has been removed from country "{country_name}"', 'success')
        else:
            flash('Player not found or not assigned to any country', 'warning')

        cursor.close()
        conn.close()
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('staff_dashboard'))

@app.route('/update_country/<db_name>', methods=['POST'])
@staff_required
def update_country(db_name):
    """Update country information"""
    if request.method == 'POST':
        country_name = request.form['country_name']
        ruler_name = request.form['ruler_name']
        government_type = request.form['government_type']
        description = request.form['description']

        try:
            # Connect to the country database
            conn_config = config.copy()
            conn_config['database'] = db_name

            conn = mysql.connector.connect(**conn_config)
            cursor = conn.cursor()

            # Update country info
            cursor.execute("""
            UPDATE country_info SET 
                name = %s, 
                ruler_name = %s, 
                government_type = %s, 
                description = %s
            WHERE id = (SELECT id FROM (SELECT id FROM country_info LIMIT 1) as temp)
            """, (country_name, ruler_name, government_type, description))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Country information updated successfully', 'success')

        except mysql.connector.Error as err:
            print(f"Error updating country info: {err}")
            flash(f'Error updating country info: {err}', 'danger')

    return redirect(url_for('staff_dashboard'))

@app.route('/add_default_action_to_player', methods=['POST'])
@staff_required
def add_default_action_to_player():
    """Staff: Add a standard/default action to a player's country action sheet"""
    player_id = request.form.get('player_id')
    standard_action_id = request.form.get('standard_action_id')
    action_number = request.form.get('action_number')

    # Basic validation
    if not player_id or not standard_action_id or not action_number:
        flash('Please select a player, a default action, and an action number.', 'danger')
        return redirect(url_for('staff_dashboard'))

    try:
        action_number = int(action_number)
    except ValueError:
        flash('Invalid action number.', 'danger')
        return redirect(url_for('staff_dashboard'))

    # Fetch player and standard action from main DB
    main_conn = get_main_db_connection()
    if not main_conn:
        flash('Database connection error (main).', 'danger')
        return redirect(url_for('staff_dashboard'))

    main_cur = main_conn.cursor(dictionary=True)
    try:
        main_cur.execute("SELECT id, username, country_db FROM users WHERE id = %s", (player_id,))
        player = main_cur.fetchone()
        if not player or not player.get('country_db'):
            flash('Selected player does not have an assigned country.', 'warning')
            return redirect(url_for('staff_dashboard'))

        main_cur.execute("SELECT * FROM standard_actions WHERE id = %s", (standard_action_id,))
        std = main_cur.fetchone()
        if not std:
            flash('Selected default action not found.', 'danger')
            return redirect(url_for('staff_dashboard'))
    finally:
        main_cur.close()
        main_conn.close()

    # Connect to player's country DB
    try:
        conn_config = config.copy()
        conn_config['database'] = player['country_db']
        cconn = mysql.connector.connect(**conn_config)
        # Ensure schema compatibility for older country DBs
        ensure_actions_is_free_column(cconn)
        cur = cconn.cursor(dictionary=True)

        # Determine stat1 and value
        stat1 = std.get('stat_type') if std.get('stat_type') else None
        stat1_value = None
        if stat1:
            try:
                cur.execute("SELECT rating FROM stats WHERE name = %s", (stat1,))
                res = cur.fetchone()
                if res:
                    stat1_value = res['rating']
            except mysql.connector.Error as err:
                print(f"Error fetching stat rating: {err}")

        # Compose description and resources
        desc_parts = [f"[Default] {std.get('project','')}" ]
        if std.get('points_cost'):
            desc_parts.append(f"Points Cost: {std.get('points_cost')}")
        if std.get('requirements'):
            desc_parts.append(f"Requirements: {std.get('requirements')}")
        if std.get('benefits'):
            desc_parts.append(f"Benefits: {std.get('benefits')}")
        description = " | ".join([p for p in desc_parts if p])
        resources_used = std.get('resource_costs') or ''

        # Upsert into actions for given action_number
        cur.execute("SELECT COUNT(*) as cnt FROM actions WHERE action_number = %s", (action_number,))
        cnt = cur.fetchone()['cnt']
        if cnt and cnt > 0:
            cur.execute(
                """
                UPDATE actions
                   SET description=%s, stat1=%s, stat1_value=%s, stat2=NULL, stat2_value=NULL,
                       advisor_used=%s, resources_used=%s, gold_spent=%s, is_free=%s
                 WHERE action_number=%s
                """,
                (description, stat1, stat1_value, False, resources_used, 0, False, action_number)
            )
            flash(f'Updated Action {action_number} for {player["username"]} with default action.', 'success')
        else:
            cur.execute(
                """
                INSERT INTO actions (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent, is_free)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (action_number, description, stat1, stat1_value, None, None, False, resources_used, 0, False)
            )
            flash(f'Added Action {action_number} for {player["username"]} with default action.', 'success')
        cconn.commit()
        cur.close()
        cconn.close()
    except mysql.connector.Error as err:
        print(f"Error adding default action to player: {err}")
        flash(f'Error adding default action: {err}', 'danger')

    return redirect(url_for('staff_dashboard'))



if __name__ == '__main__':
    # Use environment flags for debug and port to avoid exposing debug in production
    _debug = os.getenv('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    _port = int(os.getenv('FLASK_RUN_PORT', '5006'))
    app.run(debug=_debug, port=_port)


# Helper to save a single resource into a country's database
# Added to support create_starting_countries where resources are generated programmatically.
def save_resource(db_name, name, rtype, tier, natively_produced, trade):
    try:
        conn_config = config.copy()
        conn_config['database'] = db_name
        conn = connect_optional_tunnel(conn_config)
        cursor = conn.cursor()
        available = int(natively_produced or 0) + int(trade or 0)
        cursor.execute(
            """
            INSERT INTO resources (name, type, tier, natively_produced, trade, committed, not_developed, available)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name or '', rtype or '', int(tier or 0), int(natively_produced or 0), int(trade or 0), 0, 0, available)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except mysql.connector.Error as err:
        print(f"Error saving resource '{name}' for {db_name}: {err}")
        return False
