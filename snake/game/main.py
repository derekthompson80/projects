from turtle import Screen, Turtle
from snake import Snake
from food import Food
from scoreboard import Scoreboard
import time
import random

# List of colors for snake and background
COLORS = ["white", "red", "orange", "yellow", "green", "blue", "purple", "pink", "cyan", "magenta"]

# Function to get a color different from the given color
def get_different_color(current_color):
    available_colors = [color for color in COLORS if color != current_color]
    return random.choice(available_colors)

def handle_game_over(is_victory=False):
    """Handle game over scenario with options to restart or exit"""
    global game_is_on, game_paused
    
    # Pause the game but don't end it
    game_paused = True
    
    # Create a message turtle for restart/exit options
    message = Turtle()
    message.hideturtle()
    message.penup()
    message.color("white")
    message.goto(0, -50)
    
    if is_victory:
        message.goto(0, -20)
        message.write("VICTORY! You've won the game!", align="center", font=("Courier", 18, "normal"))
        message.goto(0, -50)
    
    message.write("Do you want to play again? (Y/N)", align="center", font=("Courier", 18, "normal"))
    
    # Set up key listeners for restart and quit
    screen.onkey(restart_game, "y")
    screen.onkey(restart_game, "Y")
    screen.onkey(quit_game, "n")
    screen.onkey(quit_game, "N")

def restart_game():
    """Reset the game elements and restart the game"""
    global game_is_on, game_paused, current_speed, current_bg_color, last_milestone
    
    # Reset game elements
    snake.reset()
    scoreboard.reset()
    food.refresh()
    
    # Reset snake color to white
    snake.change_color("white")
    
    # Reset background color to black
    screen.bgcolor("black")
    current_bg_color = "black"
    
    # Reset game speed
    current_speed = 0.1
    
    # Reset milestone tracker
    last_milestone = 0
    
    # Restart the game
    game_is_on = True
    game_paused = False
    
    # Clear any message turtles
    for turtle in screen.turtles():
        if turtle not in [snake.head] + snake.segments and turtle not in [food, scoreboard]:
            turtle.clear()
            turtle.hideturtle()

def quit_game():
    """Exit the game"""
    global game_is_on
    game_is_on = False
    
    # Save high score before exiting
    if scoreboard.score > scoreboard.high_score:
        scoreboard.save_high_score()
        
    screen.bye()  # Close the window immediately

screen = Screen()
screen.setup(width=600, height=600)
screen.bgcolor("black")  # Starting background color is black
screen.title("My Snake Game")
screen.tracer(0)

snake = Snake()  # Starting snake color is white (set in Snake class)
food = Food()
scoreboard = Scoreboard()

# Track the current game speed (sleep time in seconds)
current_speed = 0.1
# Track the current background color
current_bg_color = "black"
# Track the last score milestone (for color/speed changes)
last_milestone = 0

screen.listen()
screen.onkey(snake.up, "Up")
screen.onkey(snake.down, "Down")
screen.onkey(snake.left, "Left")
screen.onkey(snake.right, "Right")

game_is_on = True
game_paused = False

while game_is_on:
    screen.update()
    
    # Only process game logic if the game is not paused
    if not game_paused:
        time.sleep(current_speed)
        snake.move()

        # Detect collision with food.
        if snake.head.distance(food) < 15:
            food.refresh()
            snake.extend()
            scoreboard.increase_score()
            
            # Check if we've reached a new 10-point milestone
            if scoreboard.score % 10 == 0 and scoreboard.score > last_milestone:
                last_milestone = scoreboard.score
                
                # Change snake color
                new_snake_color = get_different_color(current_bg_color)
                snake.change_color(new_snake_color)
                
                # Change background color
                new_bg_color = get_different_color(new_snake_color)
                screen.bgcolor(new_bg_color)
                current_bg_color = new_bg_color
                
                # Increase speed (decrease sleep time)
                current_speed = max(0.01, current_speed - 0.01)  # Don't go below 0.01

        # Check for victory condition - if snake is too large, it's a win
        # A 600x600 screen with 20x20 segments can fit at most 900 segments (30x30 grid)
        # We'll use a more conservative number to account for the walls
        if len(snake.segments) >= 800:  # Almost filled the screen
            scoreboard.game_over()
            handle_game_over(is_victory=True)
            
        # Detect collision with wall.
        if snake.head.xcor() > 280 or snake.head.xcor() < -280 or snake.head.ycor() > 280 or snake.head.ycor() < -280:
            scoreboard.game_over()
            handle_game_over()

        # Detect collision with tail.
        for segment in snake.segments[1:]:
            if snake.head.distance(segment) < 10:
                scoreboard.game_over()
                handle_game_over()


# The game will continue running until the player chooses to quit
# No need for screen.exitonclick() as we have our own quit mechanism
