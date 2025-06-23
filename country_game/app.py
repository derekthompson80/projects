from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = 'therendrim_secret_key'

# MySQL connection parameters
config = {
    'user': 'root',
    'password': 'Beholder3',
    'host': 'localhost',
    'database': 'therendrim_game',
    'raise_on_warnings': True
}

def get_db_connection():
    """Get a connection to the database"""
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

# Stats routes
@app.route('/stats')
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
def add_stat():
    """Add a new stat"""
    if request.method == 'POST':
        name = request.form['name']
        rating = request.form['rating']
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
def edit_stat(id):
    """Edit an existing stat"""
    if request.method == 'POST':
        name = request.form['name']
        rating = request.form['rating']
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
def resources():
    """Display all resources"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM resources")
        resources = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('resources.html', resources=resources)
    else:
        flash('Database connection error', 'danger')
        return render_template('resources.html', resources=[])

@app.route('/resources/add', methods=['POST'])
def add_resource():
    """Add a new resource"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form['type'] if 'type' in request.form else None
        tier = request.form['tier'] if 'tier' in request.form else 0
        natively_produced = request.form['natively_produced'] if 'natively_produced' in request.form else 0
        trade = request.form['trade'] if 'trade' in request.form else 0
        committed = request.form['committed'] if 'committed' in request.form else 0
        not_developed = request.form['not_developed'] if 'not_developed' in request.form else 0
        available = request.form['available'] if 'available' in request.form else 0
        
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
def edit_resource(id):
    """Edit an existing resource"""
    if request.method == 'POST':
        name = request.form['name']
        resource_type = request.form['type'] if 'type' in request.form else None
        tier = request.form['tier'] if 'tier' in request.form else 0
        natively_produced = request.form['natively_produced'] if 'natively_produced' in request.form else 0
        trade = request.form['trade'] if 'trade' in request.form else 0
        committed = request.form['committed'] if 'committed' in request.form else 0
        not_developed = request.form['not_developed'] if 'not_developed' in request.form else 0
        available = request.form['available'] if 'available' in request.form else 0
        
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
def actions():
    """Display all actions"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM actions")
        actions = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('actions.html', actions=actions)
    else:
        flash('Database connection error', 'danger')
        return render_template('actions.html', actions=[])

@app.route('/actions/add', methods=['POST'])
def add_action():
    """Add a new action"""
    if request.method == 'POST':
        action_number = request.form['action_number']
        description = request.form['description'] if 'description' in request.form else None
        stat1 = request.form['stat1'] if 'stat1' in request.form else None
        stat1_value = request.form['stat1_value'] if 'stat1_value' in request.form else None
        stat2 = request.form['stat2'] if 'stat2' in request.form else None
        stat2_value = request.form['stat2_value'] if 'stat2_value' in request.form else None
        advisor_used = request.form['advisor_used'] == '1' if 'advisor_used' in request.form else False
        resources_used = request.form['resources_used'] if 'resources_used' in request.form else None
        gold_spent = request.form['gold_spent'] if 'gold_spent' in request.form else 0
        
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
def edit_action(id):
    """Edit an existing action"""
    if request.method == 'POST':
        action_number = request.form['action_number']
        description = request.form['description'] if 'description' in request.form else None
        stat1 = request.form['stat1'] if 'stat1' in request.form else None
        stat1_value = request.form['stat1_value'] if 'stat1_value' in request.form else None
        stat2 = request.form['stat2'] if 'stat2' in request.form else None
        stat2_value = request.form['stat2_value'] if 'stat2_value' in request.form else None
        advisor_used = request.form['advisor_used'] == '1' if 'advisor_used' in request.form else False
        resources_used = request.form['resources_used'] if 'resources_used' in request.form else None
        gold_spent = request.form['gold_spent'] if 'gold_spent' in request.form else 0
        
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
def add_project():
    """Add a new project"""
    if request.method == 'POST':
        name = request.form['name']
        effect = request.form['effect'] if 'effect' in request.form else None
        cost = request.form['cost'] if 'cost' in request.form else 0
        resources = request.form['resources'] if 'resources' in request.form else None
        status = request.form['status'] if 'status' in request.form else 'U'
        progress_per_turn = request.form['progress_per_turn'] if 'progress_per_turn' in request.form else 0
        total_needed = request.form['total_needed'] if 'total_needed' in request.form else 0
        total_progress = request.form['total_progress'] if 'total_progress' in request.form else 0
        turn_started = request.form['turn_started'] if 'turn_started' in request.form and request.form['turn_started'] else None
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Project added successfully', 'success')
        else:
            flash('Database connection error', 'danger')
        
        return redirect(url_for('projects'))

@app.route('/projects/edit/<int:id>', methods=['POST'])
def edit_project(id):
    """Edit an existing project"""
    if request.method == 'POST':
        name = request.form['name']
        effect = request.form['effect'] if 'effect' in request.form else None
        cost = request.form['cost'] if 'cost' in request.form else 0
        resources = request.form['resources'] if 'resources' in request.form else None
        status = request.form['status'] if 'status' in request.form else 'U'
        progress_per_turn = request.form['progress_per_turn'] if 'progress_per_turn' in request.form else 0
        total_needed = request.form['total_needed'] if 'total_needed' in request.form else 0
        total_progress = request.form['total_progress'] if 'total_progress' in request.form else 0
        turn_started = request.form['turn_started'] if 'turn_started' in request.form and request.form['turn_started'] else None
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE projects SET name = %s, effect = %s, cost = %s, resources = %s, status = %s, progress_per_turn = %s, total_needed = %s, total_progress = %s, turn_started = %s WHERE id = %s",
                (name, effect, cost, resources, status, progress_per_turn, total_needed, total_progress, turn_started, id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Project updated successfully', 'success')
        else:
            flash('Database connection error', 'danger')
        
        return redirect(url_for('projects'))

@app.route('/projects/delete/<int:id>')
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

if __name__ == '__main__':
    app.run(debug=True, port=5006)