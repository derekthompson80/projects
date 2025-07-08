from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
import os
import re
import random
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import glob

app = Flask(__name__)
app.secret_key = 'country_game_secret_key'

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

# MySQL connection parameters
config = {
    'user': 'spade605',
    'password': 'Beholder30',
    'host': 'spade605.mysql.pythonanywhere-services.com',
    'database': 'spade605$county_game_server',
    'raise_on_warnings': True
}

def get_db_connection():
    """Get a connection to the database"""
    try:
        # Use the current country database if one is selected
        conn_config = config.copy()
        if 'current_country_db' in session:
            conn_config['database'] = session['current_country_db']

        conn = mysql.connector.connect(**conn_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def get_main_db_connection():
    """Get a connection to the main database (spade605$county_game_server)"""
    try:
        # Always connect to the main database
        conn_config = config.copy()
        conn_config['database'] = 'spade605$county_game_server'  # Ensure we connect to the main database

        conn = mysql.connector.connect(**conn_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to main MySQL database: {err}")
        return None

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
    """Home page - redirects to login page"""
    return redirect(url_for('login'))

# Stats routes
@app.route('/stats')
@staff_required
def stats():
    """Display all stats"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM stats")
        stats = cursor.fetchall()
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

# Resources routes
@app.route('/resources')
@login_required
def resources():
    """Display all resources"""
    # Get pre-filled name from query string if provided
    pre_filled_name = request.args.get('name', '')

    # Get resource type and tier from CSV if name is provided
    pre_filled_type = ''
    pre_filled_tier = ''

    if pre_filled_name:
        try:
            import csv
            with open('staff_sheet_templete.csv', 'r') as file:
                reader = csv.reader(file)
                rows = list(reader)

                # Find resources section (starting at row 31)
                for i in range(31, len(rows)):
                    if i < len(rows) and len(rows[i]) >= 4:
                        name = rows[i][3].strip()
                        # If we find the resource, get its type and tier
                        if name == pre_filled_name:
                            pre_filled_type = rows[i][4] if len(rows[i]) > 4 else ''
                            pre_filled_tier = rows[i][5] if len(rows[i]) > 5 else ''
                            break

                        # Stop when we reach the "Committed in Detail" section
                        if name == "Committed in Detail":
                            break
        except Exception as e:
            print(f"Error loading resource details from CSV: {e}")

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
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
    """Add a new resource"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form['type'] if 'type' in request.form else None
        tier = int(request.form['tier']) if 'tier' in request.form and request.form['tier'].strip() else 0
        natively_produced = int(request.form['natively_produced']) if 'natively_produced' in request.form and request.form['natively_produced'].strip() else 0
        trade = int(request.form['trade']) if 'trade' in request.form and request.form['trade'].strip() else 0
        committed = int(request.form['committed']) if 'committed' in request.form and request.form['committed'].strip() else 0
        not_developed = int(request.form['not_developed']) if 'not_developed' in request.form and request.form['not_developed'].strip() else 0
        available = int(request.form['available']) if 'available' in request.form and request.form['available'].strip() else 0

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO resources (name, type, tier, natively_produced, trade, committed, not_developed, available) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (name, resource_type, tier, natively_produced, trade, committed, not_developed, available)
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
    """Edit an existing resource"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form['type'] if 'type' in request.form else None
        tier = int(request.form['tier']) if 'tier' in request.form and request.form['tier'].strip() else 0
        natively_produced = int(request.form['natively_produced']) if 'natively_produced' in request.form and request.form['natively_produced'].strip() else 0
        trade = int(request.form['trade']) if 'trade' in request.form and request.form['trade'].strip() else 0
        committed = int(request.form['committed']) if 'committed' in request.form and request.form['committed'].strip() else 0
        not_developed = int(request.form['not_developed']) if 'not_developed' in request.form and request.form['not_developed'].strip() else 0
        available = int(request.form['available']) if 'available' in request.form and request.form['available'].strip() else 0

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE resources SET name = %s, type = %s, tier = %s, natively_produced = %s, trade = %s, committed = %s, not_developed = %s, available = %s WHERE id = %s",
                (name, resource_type, tier, natively_produced, trade, committed, not_developed, available, id)
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

# Actions routes
@app.route('/actions')
@login_required
def actions():
    """Display all actions"""
    # Initialize all_resources list
    all_resources = []

    # Load all resources from CSV file
    try:
        import csv
        with open('staff_sheet_templete.csv', 'r') as file:
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

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM actions")
        actions = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('actions.html', actions=actions, all_resources=all_resources)
    else:
        flash('Database connection error', 'danger')
        return render_template('actions.html', actions=[], all_resources=all_resources)

@app.route('/actions/add', methods=['POST'])
@staff_required
def add_action():
    """Add a new action"""
    if request.method == 'POST':
        action_number = int(request.form['action_number']) if request.form['action_number'].strip() else 0
        description = request.form['description'] if 'description' in request.form else None
        stat1 = request.form['stat1'] if 'stat1' in request.form else None
        stat1_value = int(request.form['stat1_value']) if 'stat1_value' in request.form and request.form['stat1_value'].strip() else None
        stat2 = request.form['stat2'] if 'stat2' in request.form else None
        stat2_value = int(request.form['stat2_value']) if 'stat2_value' in request.form and request.form['stat2_value'].strip() else None
        advisor_used = request.form['advisor_used'] == '1' if 'advisor_used' in request.form else False
        resources_used = request.form['resources_used'] if 'resources_used' in request.form else None
        gold_spent = int(request.form['gold_spent']) if 'gold_spent' in request.form and request.form['gold_spent'].strip() else 0

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO actions (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Action added successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('actions'))

@app.route('/actions/edit/<int:id>', methods=['POST'])
@staff_required
def edit_action(id):
    """Edit an existing action"""
    if request.method == 'POST':
        action_number = int(request.form['action_number']) if request.form['action_number'].strip() else 0
        description = request.form['description'] if 'description' in request.form else None
        stat1 = request.form['stat1'] if 'stat1' in request.form else None
        stat1_value = int(request.form['stat1_value']) if 'stat1_value' in request.form and request.form['stat1_value'].strip() else None
        stat2 = request.form['stat2'] if 'stat2' in request.form else None
        stat2_value = int(request.form['stat2_value']) if 'stat2_value' in request.form and request.form['stat2_value'].strip() else None
        advisor_used = request.form['advisor_used'] == '1' if 'advisor_used' in request.form else False
        resources_used = request.form['resources_used'] if 'resources_used' in request.form else None
        gold_spent = int(request.form['gold_spent']) if 'gold_spent' in request.form and request.form['gold_spent'].strip() else 0

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE actions SET action_number = %s, description = %s, stat1 = %s, stat1_value = %s, stat2 = %s, stat2_value = %s, advisor_used = %s, resources_used = %s, gold_spent = %s WHERE id = %s",
                (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Action updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('actions'))

@app.route('/actions/delete/<int:id>')
@staff_required
def delete_action(id):
    """Delete an action"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM actions WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Action deleted successfully', 'success')
    else:
        flash('Database connection error', 'danger')

    return redirect(url_for('actions'))

# Projects routes
@app.route('/projects')
@login_required
def projects():
    """Display all projects"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM projects")
        projects = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('projects.html', projects=projects)
    else:
        flash('Database connection error', 'danger')
        return render_template('projects.html', projects=[])

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
    """Get a list of default countries from the CG5_Country_Descriptions.txt file"""
    countries = []
    try:
        # Read the country descriptions file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, 'CG5_Country_Descriptions.txt')

        with open(file_path, 'r') as file:
            content = file.readlines()

        # Parse the content to extract country names
        for line in content:
            line = line.strip()
            if not line or line.startswith('There are'):
                continue

            # Check if this is a country entry (starts with a number followed by a period)
            if re.match(r'^\d+\.', line):
                # Extract country name
                parts = line.split(' - ')
                if len(parts) >= 1:
                    country_info = parts[0].split(' ', 1)
                    if len(country_info) > 1:
                        country_name = country_info[1].strip()
                        # Only add if not already in the list (remove duplicates)
                        if country_name not in countries:
                            countries.append(country_name)

        # Sort countries alphabetically
        countries.sort()
        print(f"Found {len(countries)} countries in CG5_Country_Descriptions.txt")

    except Exception as e:
        print(f"Error getting default countries: {e}")
        # Fallback to the old method if there's an error
        try:
            # Get all .csv files in the 'countries_templates' directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            countries_dir = os.path.join(script_dir, 'countries_templates')
            country_files = glob.glob(os.path.join(countries_dir, '*.csv'))

            # Extract country names from filenames
            for file_path in country_files:
                # Get the filename without path and extension
                filename = os.path.basename(file_path)
                # Remove the " (Staff) - Template.csv" suffix
                country_name = filename.replace(' (Staff) - Template.csv', '')
                if country_name not in countries:  # Avoid duplicates
                    countries.append(country_name)

            # Sort countries alphabetically
            countries.sort()
            print(f"Fallback: Found {len(country_files)} country template files")
        except Exception as inner_e:
            print(f"Error in fallback method: {inner_e}")

    return countries

@app.route('/create_country')
@login_required
def create_country_form():
    """Display the country creation form"""
    default_countries = get_default_countries()
    return render_template('create_country.html', default_countries=default_countries)

def parse_country_template(template_name):
    """Parse a country template CSV file and extract relevant data"""
    template_data = {
        'country_name': template_name,
        'ruler_name': '',
        'government_type': 'Other',
        'description': '',
        'stats': {},
        'resources': []
    }

    try:
        import csv
        template_path = os.path.join('countries_templates', f"{template_name} (Staff) - Template.csv")

        with open(template_path, 'r') as file:
            reader = csv.reader(file)
            rows = list(reader)

            # Extract country info from row 2
            if len(rows) > 1 and len(rows[1]) > 8:
                template_data['country_name'] = rows[1][0] or template_name
                template_data['ruler_name'] = rows[1][1] or ''
                template_data['description'] = rows[1][7] or ''

            # Extract stats
            stats_map = {
                'Politics': 'politics',
                'Military': 'military',
                'Economics': 'economics',
                'Society': 'culture'  # Map Society to culture
            }

            for i in range(4, 14):  # Stats are in rows 5-13
                if i < len(rows) and len(rows[i]) > 1:
                    stat_name = rows[i][0].strip()
                    if stat_name in stats_map and rows[i][1].strip().isdigit():
                        template_data['stats'][stats_map[stat_name]] = int(rows[i][1])

            # Extract resources
            for i in range(31, 130):  # Resources are in rows 32-129
                if i < len(rows) and len(rows[i]) > 6:
                    resource_name = rows[i][3].strip()
                    if resource_name and resource_name != "Name" and resource_name != "":
                        resource_type = rows[i][4].strip() if len(rows[i]) > 4 else ""
                        tier = rows[i][5].strip() if len(rows[i]) > 5 else ""
                        natively_produced = rows[i][6].strip() if len(rows[i]) > 6 else "0"
                        trade = rows[i][7].strip() if len(rows[i]) > 7 else "0"

                        # Convert to integers, default to 0 if not a number
                        try:
                            natively_produced = int(natively_produced) if natively_produced.isdigit() else 0
                        except:
                            natively_produced = 0

                        try:
                            trade = int(trade) if trade.isdigit() else 0
                        except:
                            trade = 0

                        # Only add resources that are produced or traded
                        if natively_produced != 0 or trade != 0:
                            template_data['resources'].append({
                                'name': resource_name,
                                'type': resource_type,
                                'tier': tier if tier.isdigit() else 0,
                                'natively_produced': natively_produced,
                                'trade': trade
                            })

    except Exception as e:
        print(f"Error parsing country template: {e}")

    return template_data

@app.route('/create_country', methods=['POST'])
@login_required
def create_country():
    """Create a new country database and tables"""
    if request.method == 'POST':
        # Check if a template was selected
        default_country = request.form.get('default_country', '')
        template_data = {}

        if default_country:
            template_data = parse_country_template(default_country)

        # Get form data
        country_name = request.form['country_name']
        ruler_name = request.form['ruler_name']
        government_type = request.form['government_type']
        description = request.form['description']

        # Get initial stats
        politics = int(request.form['politics'])
        military = int(request.form['military'])
        economics = int(request.form['economics'])
        culture = int(request.form['culture'])

        # Get random resources if provided
        random_resources_json = request.form.get('random_resources', '')
        random_resources = []

        if random_resources_json:
            try:
                import json
                random_resources = json.loads(random_resources_json)
            except Exception as e:
                print(f"Error parsing random resources JSON: {e}")

        # Override with template data if available
        if template_data:
            # Only override ruler_name, government_type, and description if they're empty in the form
            if not ruler_name and 'ruler_name' in template_data:
                ruler_name = template_data['ruler_name']
            if government_type == 'Other' and 'government_type' in template_data:
                government_type = template_data['government_type']
            if not description and 'description' in template_data:
                description = template_data['description']

            # Override stats if they're at default values (5)
            if politics == 5 and 'politics' in template_data.get('stats', {}):
                politics = template_data['stats']['politics']
            if military == 5 and 'military' in template_data.get('stats', {}):
                military = template_data['stats']['military']
            if economics == 5 and 'economics' in template_data.get('stats', {}):
                economics = template_data['stats']['economics']
            if culture == 5 and 'culture' in template_data.get('stats', {}):
                culture = template_data['stats']['culture']

        # Validate country name (only allow alphanumeric and underscore)
        if not re.match(r'^[a-zA-Z0-9_]+$', country_name):
            flash('Country name can only contain letters, numbers, and underscores', 'danger')
            return redirect(url_for('create_country_form'))

        # Create database name (lowercase for consistency)
        db_name = f"country_{country_name.lower()}"

        # Create the database and tables
        if create_country_database(db_name):
            # Save country info
            if save_country_info(db_name, country_name, ruler_name, government_type, description):
                # Save initial stats
                if save_initial_stats(db_name, politics, military, economics, culture):
                    # Import resources from template if available
                    if template_data and 'resources' in template_data and template_data['resources']:
                        import_resources_from_template(db_name, template_data['resources'])
                    # Import random resources if available
                    elif random_resources:
                        import_resources_from_template(db_name, random_resources)

                    # Store the current country database in session
                    session['current_country_db'] = db_name
                    flash(f'Country {country_name} created successfully!', 'success')
                    return redirect(url_for('index'))

        flash('Failed to create country', 'danger')
        return redirect(url_for('create_country_form'))

def create_country_database(db_name):
    """Create a new database for the country and set up tables"""
    try:
        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Create the database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")

        # Use the new database
        cursor.execute(f"USE {db_name}")

        # Create tables (similar to db_setup.py)
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

        # Country info table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS country_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            ruler_name VARCHAR(100) NOT NULL,
            government_type VARCHAR(50),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"Error creating country database: {err}")
        return False

def save_country_info(db_name, country_name, ruler_name, government_type, description):
    """Save country information to the country_info table"""
    try:
        # Connect to the country database
        conn_config = config.copy()
        conn_config['database'] = db_name

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Insert country info
        cursor.execute("""
        INSERT INTO country_info (name, ruler_name, government_type, description)
        VALUES (%s, %s, %s, %s)
        """, (country_name, ruler_name, government_type, description))

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"Error saving country info: {err}")
        return False

def save_initial_stats(db_name, politics, military, economics, culture):
    """Save initial stats to the stats table"""
    try:
        # Connect to the country database
        conn_config = config.copy()
        conn_config['database'] = db_name

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Insert initial stats
        stats = [
            ('Politics', politics, None, 'Initial politics rating', None),
            ('Military', military, None, 'Initial military rating', None),
            ('Economics', economics, None, 'Initial economics rating', None),
            ('Culture', culture, None, 'Initial culture rating', None)
        ]

        for stat in stats:
            cursor.execute("""
            INSERT INTO stats (name, rating, modifier, notes, advisor)
            VALUES (%s, %s, %s, %s, %s)
            """, stat)

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"Error saving initial stats: {err}")
        return False

def import_resources_from_template(db_name, resources):
    """Import resources from a template into the country database"""
    try:
        # Connect to the country database
        conn_config = config.copy()
        conn_config['database'] = db_name

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Insert resources
        for resource in resources:
            # Calculate available based on natively_produced and trade
            available = resource.get('natively_produced', 0) + resource.get('trade', 0)

            cursor.execute("""
            INSERT INTO resources (name, type, tier, natively_produced, trade, committed, not_developed, available)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                resource.get('name', ''),
                resource.get('type', ''),
                resource.get('tier', 0),
                resource.get('natively_produced', 0),
                resource.get('trade', 0),
                0,  # committed
                0,  # not_developed
                available
            ))

        conn.commit()
        cursor.close()
        conn.close()

        return True
    except mysql.connector.Error as err:
        print(f"Error importing resources from template: {err}")
        return False

@app.route('/countries')
def list_countries():
    """List all available country databases"""
    countries = []

    try:
        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Get all databases that start with 'country_'
        cursor.execute("SHOW DATABASES LIKE 'country_%'")
        country_dbs = [db[0] for db in cursor.fetchall()]

        # For each country database, get the country info
        for db_name in country_dbs:
            # Connect to the country database
            cursor.execute(f"USE {db_name}")

            # Get country info
            try:
                cursor.execute("SELECT * FROM country_info LIMIT 1")
                country_data = cursor.fetchone()

                if country_data:
                    # Create a dictionary with country info
                    country = {
                        'name': country_data[1],  # Assuming name is the second column
                        'ruler_name': country_data[2],  # Assuming ruler_name is the third column
                        'government_type': country_data[3],  # Assuming government_type is the fourth column
                        'db_name': db_name
                    }
                    countries.append(country)
            except mysql.connector.Error as err:
                print(f"Error fetching country info from {db_name}: {err}")

        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        print(f"Error listing country databases: {err}")

    return render_template('select_country.html', countries=countries)

@app.route('/select_country/<db_name>')
def select_country(db_name):
    """Select a country database"""
    # Validate that the database exists and is a country database
    try:
        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        if cursor.fetchone():
            # Set the current country database in session
            session['current_country_db'] = db_name
            flash(f'Switched to country database: {db_name}', 'success')
        else:
            flash(f'Country database not found: {db_name}', 'danger')

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
        conn = mysql.connector.connect(**config)
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
                        conn = mysql.connector.connect(**config)
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
                    return redirect(url_for('player_dashboard'))
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
        from game_rules import get_all_sections, get_suggestions

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
        conn = mysql.connector.connect(**config)
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
                          government_types=government_types)

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
        conn = mysql.connector.connect(**config)
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
    conn = mysql.connector.connect(**config)
    users = []
    countries = []

    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        # Get list of available country databases
        try:
            # Connect to MySQL server (without specifying a database)
            conn_config = config.copy()
            if 'database' in conn_config:
                del conn_config['database']

            conn2 = mysql.connector.connect(**conn_config)
            cursor2 = conn2.cursor(dictionary=True)

            # Get all databases that start with 'country_'
            cursor2.execute("SHOW DATABASES LIKE 'country_%'")
            country_dbs = [list(db.values())[0] for db in cursor2.fetchall()]

            # For each country database, get the country info
            for db_name in country_dbs:
                # Connect to the country database
                cursor2.execute(f"USE {db_name}")

                # Get country info
                try:
                    cursor2.execute("SELECT * FROM country_info LIMIT 1")
                    country_data = cursor2.fetchone()

                    if country_data:
                        # Create a dictionary with country info
                        country = {
                            'name': country_data['name'],
                            'db_name': db_name
                        }
                        countries.append(country)
                except mysql.connector.Error as err:
                    print(f"Error fetching country info from {db_name}: {err}")

            cursor2.close()
            conn2.close()
        except mysql.connector.Error as err:
            print(f"Error listing country databases: {err}")

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

        conn = mysql.connector.connect(**config)
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

        conn = mysql.connector.connect(**config)
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

    conn = mysql.connector.connect(**config)
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
@app.route('/player_dashboard')
@login_required
def player_dashboard():
    """Player dashboard for submitting actions and messaging staff"""
    if session.get('is_staff'):
        flash('Staff members should use the Staff Dashboard', 'warning')
        return redirect(url_for('staff_dashboard'))

    # Get player's recent actions
    actions = []
    messages = []
    politics_rating = 0
    max_actions = 2  # Default to 2 actions

    # Get actions from the country database
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        # Get recent actions
        cursor.execute("SELECT * FROM actions ORDER BY id DESC LIMIT 10")
        actions = cursor.fetchall()

        # Get politics stat to determine max actions
        cursor.execute("SELECT * FROM stats WHERE name = 'Politics'")
        politics_stat = cursor.fetchone()
        if politics_stat:
            politics_rating = politics_stat['rating']
            # Determine max actions based on politics rating
            if politics_rating >= 5:
                max_actions = 4
            elif politics_rating >= 3:
                max_actions = 3

        cursor.close()
        conn.close()

    # Get messages from the main database
    try:
        main_conn = get_main_db_connection()
        if main_conn:
            main_cursor = main_conn.cursor(dictionary=True)

            # Get messages for this user
            user_id = session.get('user_id')
            main_cursor.execute("""
                SELECT m.*, 
                       sender.username as sender_username, 
                       recipient.username as recipient_username 
                FROM messages m
                JOIN users sender ON m.sender_id = sender.id
                JOIN users recipient ON m.recipient_id = recipient.id
                WHERE m.sender_id = %s OR m.recipient_id = %s
                ORDER BY m.created_at DESC
            """, (user_id, user_id))
            messages = main_cursor.fetchall()

            main_cursor.close()
            main_conn.close()
    except mysql.connector.Error as err:
        print(f"Error fetching messages: {err}")
        # If there's an error (like table doesn't exist), just continue with empty messages list

    # Initialize all_resources list
    all_resources = []

    # Get resources from the player's country database
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        # Get resources from the database
        cursor.execute("SELECT * FROM resources")
        db_resources = cursor.fetchall()

        # Convert to the format expected by the template
        for resource in db_resources:
            all_resources.append({
                'name': resource['name'],
                'type': resource['type'],
                'tier': resource['tier']
            })

        cursor.close()
        conn.close()

    # If no resources found in database, fall back to CSV (for backward compatibility)
    if not all_resources:
        try:
            import csv
            with open('staff_sheet_templete.csv', 'r') as file:
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

    # Get all stats for dropdown
    stats = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM stats")
        stats = cursor.fetchall()

        # Get current season
        current_season = None
        try:
            cursor.execute("SELECT * FROM seasons WHERE current = TRUE LIMIT 1")
            current_season = cursor.fetchone()
        except:
            # Table might not exist yet
            pass

        # Get country achievements
        achievements = []
        try:
            country_id = session.get('country_db')
            if country_id:
                cursor.execute("SELECT * FROM achievements WHERE country_id = %s", (country_id,))
                achievements = cursor.fetchall()
        except:
            # Table might not exist yet
            pass

        cursor.close()
        conn.close()

    return render_template('player_dashboard.html', 
                          actions=actions, 
                          messages=messages, 
                          max_actions=max_actions, 
                          politics_rating=politics_rating, 
                          all_resources=all_resources, 
                          stats=stats,
                          current_season=current_season,
                          achievements=achievements)

@app.route('/submit_player_action', methods=['POST'])
@login_required
def submit_player_action():
    """Submit a player action"""
    if session.get('is_staff'):
        flash('Staff members cannot submit player actions', 'danger')
        return redirect(url_for('staff_dashboard'))

    if request.method == 'POST':
        action_number = int(request.form['action_number']) if request.form['action_number'].strip() else 0
        description = request.form['description'] if 'description' in request.form else None
        stat1 = request.form['stat1'] if 'stat1' in request.form else None
        stat1_value = None
        stat2 = request.form['stat2'] if 'stat2' in request.form else None
        stat2_value = None
        advisor_used = request.form['advisor_used'] == '1' if 'advisor_used' in request.form else False
        resources_used = request.form['resources_used'] if 'resources_used' in request.form else None
        gold_spent = int(request.form['gold_spent']) if 'gold_spent' in request.form and request.form['gold_spent'].strip() else 0
        is_free = request.form['is_free'] == '1' if 'is_free' in request.form else False

        # Check if action number is valid based on politics rating
        politics_rating = 0
        max_actions = 2  # Default to 2 actions

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)

            # Get politics stat to determine max actions
            cursor.execute("SELECT * FROM stats WHERE name = 'Politics'")
            politics_stat = cursor.fetchone()
            if politics_stat:
                politics_rating = politics_stat['rating']
                # Determine max actions based on politics rating
                if politics_rating >= 5:
                    max_actions = 4
                elif politics_rating >= 3:
                    max_actions = 3

            # Get stat values from database if stat names are provided
            if stat1:
                cursor.execute("SELECT rating FROM stats WHERE name = %s", (stat1,))
                stat_result = cursor.fetchone()
                if stat_result:
                    stat1_value = stat_result['rating']

            if stat2:
                cursor.execute("SELECT rating FROM stats WHERE name = %s", (stat2,))
                stat_result = cursor.fetchone()
                if stat_result:
                    stat2_value = stat_result['rating']

            # Check for stat usage limits (each stat can only be used twice per turn)
            if stat1 or stat2:
                # Get current actions to check stat usage
                cursor.execute("SELECT stat1, stat2 FROM actions WHERE is_free = 0")
                current_actions = cursor.fetchall()

                # Count stat usage
                stat_usage = {}
                for action in current_actions:
                    if action['stat1']:
                        stat_usage[action['stat1']] = stat_usage.get(action['stat1'], 0) + 1
                    if action['stat2']:
                        stat_usage[action['stat2']] = stat_usage.get(action['stat2'], 0) + 1

                # Check if adding this action would exceed the limit
                if not is_free:  # Only check for non-free actions
                    if stat1 and stat_usage.get(stat1, 0) >= 2:
                        flash(f'You have already used {stat1} twice this turn. Each stat can only be used twice per turn.', 'danger')
                        cursor.close()
                        conn.close()
                        return redirect(url_for('player_dashboard'))

                    if stat2 and stat_usage.get(stat2, 0) >= 2:
                        flash(f'You have already used {stat2} twice this turn. Each stat can only be used twice per turn.', 'danger')
                        cursor.close()
                        conn.close()
                        return redirect(url_for('player_dashboard'))

            # Check if action number is valid for non-free actions
            if not is_free and action_number > max_actions:
                flash(f'Invalid action number. You can only submit up to {max_actions} actions with your current Politics rating of {politics_rating}.', 'danger')
                cursor.close()
                conn.close()
                return redirect(url_for('player_dashboard'))

            # Count existing actions to ensure not exceeding max
            cursor.execute("SELECT COUNT(*) as count FROM actions WHERE action_number = %s", (action_number,))
            action_count = cursor.fetchone()['count']

            if action_count > 0:
                # Action with this number already exists, allow update
                cursor.execute(
                    "UPDATE actions SET description = %s, stat1 = %s, stat1_value = %s, stat2 = %s, stat2_value = %s, advisor_used = %s, resources_used = %s, gold_spent = %s, is_free = %s WHERE action_number = %s",
                    (description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent, is_free, action_number)
                )
                flash('Action updated successfully', 'success')
            else:
                # New action
                cursor.execute(
                    "INSERT INTO actions (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent, is_free) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (action_number, description, stat1, stat1_value, stat2, stat2_value, advisor_used, resources_used, gold_spent, is_free)
                )
                flash('Action submitted successfully', 'success')

            conn.commit()
            cursor.close()
            conn.close()
        else:
            flash('Database connection error', 'danger')

        return redirect(url_for('player_dashboard'))

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
            conn = mysql.connector.connect(**config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE role = 'staff' LIMIT 1")
            staff = cursor.fetchone()
            cursor.close()
            conn.close()

            if staff:
                recipient_id = staff['id']
            else:
                flash('No staff members available to receive messages', 'danger')
                return redirect(url_for('player_dashboard' if not session.get('is_staff') else 'staff_dashboard'))

        # Insert the message
        try:
            conn = mysql.connector.connect(**config)
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
            return redirect(url_for('player_dashboard'))

# Staff routes
@app.route('/create_countries_from_descriptions')
@staff_required
def create_countries_from_descriptions():
    """Create countries based on descriptions in CG5_Country_Descriptions.txt"""
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
                    }
                    descriptions.append(current_description)
            elif current_description and not line.startswith('There are'):
                # Append to the description of the current country
                if current_description['description']:
                    current_description['description'] += ' ' + line
                else:
                    current_description['description'] = line

        # Create countries from descriptions
        created_countries = []
        for desc in descriptions:
            # Create database name (lowercase for consistency)
            country_name = desc['name']
            db_name = f"country_{country_name.lower().replace(' ', '_')}"

            # Check if country already exists
            conn_config = config.copy()
            if 'database' in conn_config:
                del conn_config['database']

            conn = mysql.connector.connect(**conn_config)
            cursor = conn.cursor()

            cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
            if cursor.fetchone():
                # Country already exists, skip
                cursor.close()
                conn.close()
                continue

            # Create the database and tables
            if create_country_database(db_name):
                # Generate random stats between 1-3
                politics = random.randint(1, 3)
                military = random.randint(1, 3)
                economics = random.randint(1, 3)
                culture = random.randint(1, 3)

                # Save country info
                if save_country_info(db_name, country_name, f"Ruler of {country_name}", desc['government_type'], desc['description']):
                    # Save initial stats
                    if save_initial_stats(db_name, politics, military, economics, culture):
                        # Generate random resources between 5-12
                        import json

                        # Sample resources for random generation
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

                        # Generate a random number of resources (between 5 and 12)
                        num_resources = random.randint(5, 12)

                        # Shuffle the resources array
                        random.shuffle(all_resources)

                        # Take the first num_resources
                        selected_resources = all_resources[:num_resources]

                        # Generate random values for natively_produced and trade
                        for resource in selected_resources:
                            resource["natively_produced"] = random.randint(1, 3)
                            resource["trade"] = random.randint(0, 1)

                        # Import resources
                        import_resources_from_template(db_name, selected_resources)

                        created_countries.append(country_name)

        if created_countries:
            flash(f'Successfully created {len(created_countries)} countries from descriptions: {", ".join(created_countries)}', 'success')
        else:
            flash('No new countries were created. All countries from descriptions may already exist.', 'info')

        return redirect(url_for('staff_dashboard'))

    except Exception as e:
        flash(f'Error creating countries from descriptions: {str(e)}', 'danger')
        return redirect(url_for('staff_dashboard'))

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
        conn = mysql.connector.connect(**config)
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
            with open('staff_sheet_templete.csv', 'r') as file:
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

        # Connect to MySQL server for country list
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor(dictionary=True)

        # Get all databases that start with 'country_'
        cursor.execute("SHOW DATABASES LIKE 'country_%'")
        # When using dictionary=True, we need to get the first value from each dictionary
        country_dbs = [list(db.values())[0] for db in cursor.fetchall()]

        # For each country database, get the country info
        for db_name in country_dbs:
            # Connect to the country database
            cursor.execute(f"USE {db_name}")

            # Get country info
            try:
                cursor.execute("SELECT * FROM country_info LIMIT 1")
                country_data = cursor.fetchone()

                if country_data:
                    # Create a dictionary with country info
                    country = {
                        'name': country_data['name'],
                        'ruler_name': country_data['ruler_name'],
                        'government_type': country_data['government_type'],
                        'description': country_data['description'] if 'description' in country_data else '',
                        'db_name': db_name,
                        'assigned_player': None,
                        'is_open_for_selection': True
                    }
                    countries.append(country)
            except mysql.connector.Error as err:
                print(f"Error fetching country info from {db_name}: {err}")

        # Get player assignments for countries
        try:
            # Switch back to the main database
            cursor.execute("USE spade605$county_game_server")

            # Get all users with assigned countries
            cursor.execute("SELECT id, username, country_db FROM users WHERE country_db IS NOT NULL AND country_db != ''")
            assigned_countries = cursor.fetchall()

            # Update country objects with player information
            for assignment in assigned_countries:
                for country in countries:
                    if country['db_name'] == assignment['country_db']:
                        country['assigned_player'] = {
                            'id': assignment['id'],
                            'username': assignment['username']
                        }
                        country['is_open_for_selection'] = False
                        break

            # Update players_with_countries list with country names
            for player_info in players_with_countries:
                if player_info['country_db']:
                    for country in countries:
                        if country['db_name'] == player_info['country_db']:
                            player_info['country_name'] = country['name']
                            break
        except mysql.connector.Error as err:
            print(f"Error fetching country assignments: {err}")

        cursor.close()
        conn.close()

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
                          cpu_quota_info=cpu_quota_info)

@app.route('/delete_country/<db_name>')
@staff_required
def delete_country(db_name):
    """Delete a country database"""
    try:
        # Validate that the database exists and is a country database
        if not db_name.startswith('country_'):
            flash('Invalid country database name', 'danger')
            return redirect(url_for('staff_dashboard'))

        # Connect to MySQL server (without specifying a database)
        conn_config = config.copy()
        if 'database' in conn_config:
            del conn_config['database']

        conn = mysql.connector.connect(**conn_config)
        cursor = conn.cursor()

        # Check if the database exists
        cursor.execute("SHOW DATABASES LIKE %s", (db_name,))
        if cursor.fetchone():
            # Drop the database
            cursor.execute(f"DROP DATABASE {db_name}")
            flash(f'Country database {db_name} has been deleted', 'success')

            # If this was the current country, clear the selection
            if session.get('current_country_db') == db_name:
                session.pop('current_country_db', None)
        else:
            flash(f'Country database not found: {db_name}', 'danger')

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

@app.route('/player_actions')
@staff_required
def player_actions():
    """View all player actions and respond to them"""
    player_actions = []

    # Connect to country database for game data
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)

        # Get all player actions
        cursor.execute("SELECT * FROM actions ORDER BY id DESC")
        player_actions = cursor.fetchall()

        cursor.close()
        conn.close()

    return render_template('player_actions.html', player_actions=player_actions)

@app.route('/respond_to_action/<int:action_id>', methods=['POST'])
@staff_required
def respond_to_action(action_id):
    """Respond to a player action"""
    if request.method == 'POST':
        response = request.form['response']

        # Connect to country database
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # Update the action with the staff response
            cursor.execute(
                "UPDATE actions SET staff_response = %s, response_date = CURRENT_TIMESTAMP WHERE id = %s",
                (response, action_id)
            )

            conn.commit()
            cursor.close()
            conn.close()

            flash('Response submitted successfully', 'success')
        else:
            flash('Database connection error', 'danger')

    return redirect(url_for('player_actions'))

if __name__ == '__main__':
    app.run(debug=True, port=5006)
