from turtle import Turtle
import os
ALIGNMENT = "center"
FONT = ("Courier", 24, "normal")
HIGH_SCORE_FILE = "high_score.txt"


class Scoreboard(Turtle):

    def __init__(self):
        super().__init__()
        self.score = 0
        self.high_score = self.load_high_score()
        self.color("white")
        self.penup()
        self.goto(0, 270)
        self.hideturtle()
        self.update_scoreboard()

    def update_scoreboard(self):
        self.clear()
        self.write(f"Score: {self.score} High Score: {self.high_score}", align=ALIGNMENT, font=FONT)

    def game_over(self):
        self.goto(0, 0)
        self.write("GAME OVER", align=ALIGNMENT, font=FONT)
        
        # Check if current score is a new high score
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
            self.goto(0, -100)
            self.write(f"NEW HIGH SCORE: {self.high_score}!", align=ALIGNMENT, font=FONT)

    def increase_score(self):
        self.score += 1
        self.update_scoreboard()
        
    def reset(self):
        # Check if current score is a new high score before resetting
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        self.score = 0
        self.goto(0, 270)  # Reset position to top of screen
        self.update_scoreboard()
        
    def load_high_score(self):
        """Load high score from file or return 0 if file doesn't exist"""
        try:
            if os.path.exists(HIGH_SCORE_FILE):
                with open(HIGH_SCORE_FILE, "r") as file:
                    return int(file.read())
            return 0
        except (ValueError, FileNotFoundError):
            return 0
            
    def save_high_score(self):
        """Save high score to file"""
        with open(HIGH_SCORE_FILE, "w") as file:
            file.write(str(self.high_score))
