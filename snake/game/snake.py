from turtle import Turtle

STARTING_POSITIONS = [(0, 0), (-20, 0), (-40, 0)]
MOVE_DISTANCE = 20
UP = 90
DOWN = 270
LEFT = 180
RIGHT = 0

class Snake:
    def __init__(self):
        self.segments = []
        self.current_color = "white"
        self.create_snake()
        self.head = self.segments[0]
        
    def reset(self):
        # Hide all segments and clear the segments list
        for segment in self.segments:
            segment.goto(1000, 1000)  # Move off-screen
            segment.hideturtle()
        self.segments.clear()
        # Create a new snake
        self.create_snake()
        self.head = self.segments[0]

    def create_snake(self):
        for position in STARTING_POSITIONS:
            self.add_segment(position)

    def add_segment(self, position):
        new_segment = Turtle("square")
        new_segment.color(self.current_color)
        new_segment.penup()
        new_segment.goto(position)
        self.segments.append(new_segment)
        
    def change_color(self, new_color):
        """Change the color of all snake segments"""
        self.current_color = new_color
        for segment in self.segments:
            segment.color(new_color)
            
    def get_color(self):
        """Return the current color of the snake"""
        return self.current_color

    def extend(self):
        # Add a new segment to the snake
        self.add_segment(self.segments[-1].position())

    def move(self):
        # Move the snake forward
        for seg_num in range(len(self.segments) - 1, 0, -1):
            new_x = self.segments[seg_num - 1].xcor()
            new_y = self.segments[seg_num - 1].ycor()
            self.segments[seg_num].goto(new_x, new_y)
        self.head.forward(MOVE_DISTANCE)

    def up(self):
        if self.head.heading() != DOWN:
            self.head.setheading(UP)

    def down(self):
        if self.head.heading() != UP:
            self.head.setheading(DOWN)

    def left(self):
        if self.head.heading() != RIGHT:
            self.head.setheading(LEFT)

    def right(self):
        if self.head.heading() != LEFT:
            self.head.setheading(RIGHT)