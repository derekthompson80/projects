from turtle import Screen, Turtle
from snake import Snake
from food import Food
from scoreboard import Scoreboard
import time

def handle_game_over():
    """Handle game over scenario with options to restart or exit"""
    global game_is_on
    
    # Create a message turtle for restart/exit options
    message = Turtle()
    message.hideturtle()
    message.penup()
    message.color("white")
    message.goto(0, -50)
    message.write("Press 'R' to restart or 'Q' to quit", align="center", font=("Courier", 18, "normal"))
    
    # Set up key listeners for restart and quit
    screen.onkey(restart_game, "r")
    screen.onkey(restart_game, "R")
    screen.onkey(quit_game, "q")
    screen.onkey(quit_game, "Q")

def restart_game():
    """Reset the game elements and restart the game"""
    global game_is_on
    
    # Reset game elements
    snake.reset()
    scoreboard.reset()
    food.refresh()
    
    # Restart the game
    game_is_on = True
    
    # Clear any message turtles
    for turtle in screen.turtles():
        if turtle not in [snake.head] + snake.segments and turtle not in [food, scoreboard]:
            turtle.clear()
            turtle.hideturtle()

def quit_game():
    """Exit the game"""
    global game_is_on
    game_is_on = False
    screen.bye()  # Close the window immediately

screen = Screen()
screen.setup(width=600, height=600)
screen.bgcolor("black")
screen.title("My Snake Game")
screen.tracer(0)

snake = Snake()
food = Food()
scoreboard = Scoreboard()

screen.listen()
screen.onkey(snake.up, "Up")
screen.onkey(snake.down, "Down")
screen.onkey(snake.left, "Left")
screen.onkey(snake.right, "Right")

game_is_on = True
while game_is_on:
    screen.update()
    time.sleep(0.1)
    snake.move()

    #Detect collision with food.
    if snake.head.distance(food) < 15:
        food.refresh()
        snake.extend()
        scoreboard.increase_score()

    #Detect collision with wall.
    if snake.head.xcor() > 280 or snake.head.xcor() < -280 or snake.head.ycor() > 280 or snake.head.ycor() < -280:
        game_is_on = False
        scoreboard.game_over()
        handle_game_over()

    #Detect collision with tail.
    for segment in snake.segments[1:]:
        if snake.head.distance(segment) < 10:
            game_is_on = False
            scoreboard.game_over()
            handle_game_over()


# The game will continue running until the player chooses to quit
# No need for screen.exitonclick() as we have our own quit mechanism
