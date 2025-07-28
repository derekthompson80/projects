# Snake Game

A simple snake game implemented using Python's Turtle graphics.

## Changes Made

The following changes were made to convert the web-based Flask implementation to a local implementation:

1. Created a proper `Snake` class implementation in `snake.py` based on the requirements in `main.py`
2. Updated the import statement in `main.py` to use the local `Snake` class implementation
3. Removed the Flask implementation files:
   - Removed `app.py` (backed up to `app.py.bak`)
   - Removed templates directory (backed up to `templates.bak`)
   - Removed static directory (backed up to `static.bak`)

## How to Run

To run the snake game locally:

1. Navigate to the game directory
2. Run `python main.py`

## Game Controls

- Use the arrow keys to control the snake:
  - Up arrow: Move up
  - Down arrow: Move down
  - Left arrow: Move left
  - Right arrow: Move right

## Game Rules

- The snake moves continuously in the direction it's facing
- Eat food to grow longer and increase your score
- Avoid hitting the walls or the snake's own tail
- The game ends when the snake hits a wall or its own tail or no more moves can be made