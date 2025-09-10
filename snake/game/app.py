"""
Snake Game - Flask Implementation

This module implements a Snake game using Flask for the backend and JavaScript for the frontend.
The game is played in a web browser, with the server handling game state and logic.

This implementation consolidates functionality from the original turtle-based implementation
(main.py, food.py, scoreboard.py) into a single Flask application.
"""

from flask import Flask, render_template, request, session, jsonify
import random
import os

app = Flask(__name__)
app.secret_key = 'snake_game_secret_key'  # Change this in production!

# Game Constants
HIGH_SCORE_FILE = "high_score.txt"
GRID_SIZE = 600
MOVE_DISTANCE = 20
GRID_BOUNDARY = (GRID_SIZE // 2) - MOVE_DISTANCE  # Boundary for wall collision
STARTING_POSITIONS = [[0, 0], [-20, 0], [-40, 0]]  # Starting positions
DEFAULT_FOOD_POSITION = [100, 100]  # Default food position if none in session

# Helper Functions
# ------------------

def load_high_score():
    """Load high score from file or return 0 if file doesn't exist"""
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as file:
                return int(file.read())
        return 0
    except (ValueError, FileNotFoundError):
        return 0

def save_high_score(high_score):
    """Save high score to file"""
    with open(HIGH_SCORE_FILE, "w") as file:
        file.write(str(high_score))

def generate_food_position():
    """Generate a random food position within the grid boundaries"""
    food_x = random.randint(-GRID_BOUNDARY, GRID_BOUNDARY)
    food_y = random.randint(-GRID_BOUNDARY, GRID_BOUNDARY)
    return [food_x, food_y]

# Game State Management
# -------------------

def get_game_state():
    """Get the current game state from the session"""
    return {
        'snake': session.get('snake', STARTING_POSITIONS.copy()),
        'food_position': session.get('food_position', DEFAULT_FOOD_POSITION),
        'score': session.get('score', 0),
        'game_over': session.get('game_over', False),
        'game_paused': session.get('game_paused', False),
        'high_score': session.get('high_score', load_high_score())
    }

def update_high_score(score, high_score):
    """Update high score if the current score is higher"""
    if score > high_score:
        high_score = score
        session['high_score'] = high_score
        save_high_score(high_score)
    return high_score

def handle_game_over(reason, score, high_score):
    """Handle game over state and return appropriate response"""
    session['game_over'] = True
    high_score = update_high_score(score, high_score)

    return jsonify({
        'message': 'game over',
        'reason': reason,
        'score': score,
        'high_score': high_score
    })

# Route Handlers
# -------------

@app.route('/')
def index():
    """Initialize game state and render the main game page"""
    # Reset game state when accessing the main page
    session['snake'] = STARTING_POSITIONS.copy()
    session['food_position'] = generate_food_position()
    session['score'] = 0
    session['game_over'] = False
    session['game_paused'] = False
    session['high_score'] = load_high_score()

    return render_template('index.html', high_score=session['high_score'])

@app.route('/move', methods=['POST'])
def move():
    """Handle snake movement based on direction input"""
    direction = request.form.get('direction')

    # Get game state from session
    state = get_game_state()
    snake = state['snake']
    food_position = state['food_position']
    score = state['score']
    game_over = state['game_over']
    game_paused = state['game_paused']
    high_score = state['high_score']

    if game_over:
        return jsonify({'message': 'game over'})

    if game_paused:
        return jsonify({'message': 'game paused'})

    # Move the snake (update positions)
    # First, move all segments except the head
    for i in range(len(snake) - 1, 0, -1):
        snake[i][0] = snake[i-1][0]
        snake[i][1] = snake[i-1][1]

    # Then move the head based on direction
    if direction == 'up':
        snake[0][1] += MOVE_DISTANCE  # Move up (y increases)
    elif direction == 'down':
        snake[0][1] -= MOVE_DISTANCE  # Move down (y decreases)
    elif direction == 'left':
        snake[0][0] -= MOVE_DISTANCE  # Move left (x decreases)
    elif direction == 'right':
        snake[0][0] += MOVE_DISTANCE  # Move right (x increases)

    # Check for wall collision
    if (snake[0][0] > GRID_BOUNDARY or snake[0][0] < -GRID_BOUNDARY or 
        snake[0][1] > GRID_BOUNDARY or snake[0][1] < -GRID_BOUNDARY):
        return handle_game_over('wall collision', score, high_score)

    # Check for self collision
    head = snake[0]
    for segment in snake[1:]:
        if head[0] == segment[0] and head[1] == segment[1]:
            return handle_game_over('self collision', score, high_score)

    # Collision detection with food
    head_x, head_y = snake[0]
    food_x, food_y = food_position
    distance = ((head_x - food_x) ** 2 + (head_y - food_y) ** 2) ** 0.5

    if distance < MOVE_DISTANCE:  # If head is close to food
        score += 1
        session['score'] = score
        session['food_position'] = generate_food_position()

        # Extend the snake by adding a new segment at the end
        tail = snake[-1]
        snake.append([tail[0], tail[1]])  # Add a new segment at the same position as the tail

        # Check for victory condition - if snake is too large, it's a win
        if len(snake) >= 800:  # Almost filled the screen
            return handle_game_over('victory', score, high_score)

    # Update session with new snake positions
    session['snake'] = snake

    return jsonify({
        'message': 'moved',
        'score': score,
        'high_score': high_score
    })

@app.route('/get_state')
def get_state():
    """Return the current game state as JSON"""
    state = get_game_state()
    return jsonify({
        'snake': state['snake'],
        'food': state['food_position'],
        'score': state['score'],
        'game_over': state['game_over'],
        'game_paused': state['game_paused'],
        'high_score': state['high_score']
    })

@app.route('/reset_game', methods=['POST'])
def reset_game():
    """Reset the game state while preserving the high score"""
    # Reset game state
    session['snake'] = STARTING_POSITIONS.copy()
    session['food_position'] = generate_food_position()
    session['score'] = 0
    session['game_over'] = False
    session['game_paused'] = False

    # Keep the high score
    high_score = session.get('high_score', load_high_score())

    return jsonify({
        'message': 'game reset',
        'high_score': high_score
    })

@app.route('/pause_game', methods=['POST'])
def pause_game():
    """Pause the game by setting the game_paused flag"""
    session['game_paused'] = True
    return jsonify({
        'message': 'game paused'
    })

@app.route('/resume_game', methods=['POST'])
def resume_game():
    """Resume the game by clearing the game_paused flag"""
    session['game_paused'] = False
    return jsonify({
        'message': 'game resumed'
    })

@app.route('/instructions')
def instructions():
    """Render the game instructions page"""
    # Render the instructions page
    return render_template('instructions.html')

if __name__ == '__main__':
    app.run(debug=True, port=5003)
