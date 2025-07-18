from flask import Flask, render_template, request, session, jsonify
import random

app = Flask(__name__)
app.secret_key = 'your secret key'  # Change this!

@app.route('/')
def index():
    if 'snake' not in session:
        # Initialize snake with starting positions
        session['snake'] = [[0, 0], [10, 0], [20, 0]]  # Starting positions
        # Generate random food position
        food_x = random.randint(-280, 280)
        food_y = random.randint(-280, 280)
        session['food_position'] = [food_x, food_y]
        session['score'] = 0
        session['game_over'] = False

    return render_template('index.html')

@app.route('/move', methods=['POST'])
def move():
    direction = request.form['direction']

    # Get game state from session
    snake = session.get('snake', [[0, 0], [10, 0], [20, 0]])  # Default starting positions
    food_position = session.get('food_position', [100, 100])  # Default food position
    score = session.get('score', 0)
    game_over = session.get('game_over', False)

    if game_over:
        return jsonify({'message': 'game over'})

    # Print debug information
    print(f"Direction: {direction}")
    print(f"Snake before move: {snake}")

    # Move the snake (update positions)
    # First, move all segments except the head
    for i in range(len(snake) - 1, 0, -1):
        snake[i][0] = snake[i-1][0]
        snake[i][1] = snake[i-1][1]

    # Then move the head based on direction
    if direction == 'up':
        snake[0][1] -= 20  # Move up (y decreases)
    elif direction == 'down':
        snake[0][1] += 20  # Move down (y increases)
    elif direction == 'left':
        snake[0][0] -= 20  # Move left (x decreases)
    elif direction == 'right':
        snake[0][0] += 20  # Move right (x increases)

    # Print debug information
    print(f"Snake after move: {snake}")

    # Collision detection with food
    head_x, head_y = snake[0]
    food_x, food_y = food_position
    distance = ((head_x - food_x) ** 2 + (head_y - food_y) ** 2) ** 0.5

    if distance < 20:  # If head is close to food
        score += 1
        session['score'] = score

        # Generate new food position
        new_food_x = random.randint(-280, 280)
        new_food_y = random.randint(-280, 280)
        session['food_position'] = [new_food_x, new_food_y]

        # Extend the snake by adding a new segment at the end
        tail = snake[-1]
        snake.append([tail[0], tail[1]])  # Add a new segment at the same position as the tail

    # Update session with new snake positions
    session['snake'] = snake

    return jsonify({'message': 'moved'})

@app.route('/get_state')
def get_state():
    snake = session.get('snake', [[0, 0], [10, 0], [20, 0]])  # Default starting positions if not in session
    food_position = session.get('food_position', [100, 100])  # Default food position if not in session
    score = session.get('score', 0)
    game_over = session.get('game_over', False)

    # Print debug information
    print(f"Snake positions: {snake}")
    print(f"Food position: {food_position}")
    print(f"Score: {score}")
    print(f"Game over: {game_over}")

    return jsonify({
        'snake': snake,
        'food': food_position,
        'score': score,
        'game_over': game_over
    })

if __name__ == '__main__':
    app.run(debug=True, port=5003)
