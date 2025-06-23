from turtle import Turtle, Screen
import prettytable as pt
timmy = Turtle()
timmy.shape("turtle")
timmy.color("green")
timmy.forward(100)

myScreen = Screen()


print(myScreen.canvheight)
myScreen.exitonclick()

table = pt.Table()