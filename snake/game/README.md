# Snake Game - Flask Web Application

This is a web-based implementation of the classic Snake game using Flask and JavaScript.

## Overview

The Snake game has been refactored from a desktop application using Python's Turtle graphics to a web application using Flask for the backend and JavaScript/HTML/CSS for the frontend.

## Features

- Classic Snake gameplay
- High score tracking
- Responsive controls
- Game over detection (wall collision and self collision)
- Reset functionality
- Visual feedback (score display, game over message)

## How to Play

1. Use the arrow keys to control the snake:
   - ↑ - Move Up
   - ↓ - Move Down
   - ← - Move Left
   - → - Move Right

2. Eat the food (red circle) to grow longer and increase your score
3. Avoid hitting the walls or yourself
4. Try to beat your high score!

## Running the Game

1. Make sure you have Flask installed:
   ```
   pip install flask
   ```

2. Run the Flask application:
   ```
   python app.py
   ```

3. Open your web browser and navigate to:
   ```
   http://localhost:5003
   ```

## Technical Implementation

### Backend (Flask)

- `app.py`: Flask application with routes for game state management
- High score persistence using a text file
- Game logic for snake movement, collision detection, and scoring

### Frontend (JavaScript/HTML/CSS)

- `templates/index.html`: Game interface with canvas and controls
- `static/snake.js`: JavaScript implementation of the game
- Canvas-based rendering of the snake and food
- Keyboard input handling
- Communication with the Flask backend via fetch API

## Changes from Original Implementation

The original implementation used Python's Turtle graphics library for rendering and game logic. The new implementation:

1. Separates the frontend (JavaScript) and backend (Flask) concerns
2. Uses a canvas element for rendering instead of Turtle graphics
3. Maintains the same gameplay mechanics and features
4. Adds a more user-friendly interface with instructions and controls

## Files

- `app.py`: Flask application
- `templates/index.html`: HTML template for the game
- `static/snake.js`: JavaScript implementation of the game
- `high_score.txt`: File to store the high score

## Future Improvements

- Add difficulty levels
- Add sound effects
- Implement mobile-friendly controls
- Add multiplayer functionality