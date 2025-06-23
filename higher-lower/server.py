from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Generate a random number between 0 and 9
random_number = random.randint(0, 9)
print(f"Random number: {random_number}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check():
    guess = int(request.form['guess'])
    if guess < random_number:
        return render_template('too_low.html')
    elif guess > random_number:
        return render_template('too_high.html')
    else:
        return render_template('correct.html')

# Keep the original route for backward compatibility
@app.route('/<int:guess>')
def check_guess(guess):
    if guess < random_number:
        return render_template('too_low.html')
    elif guess > random_number:
        return render_template('too_high.html')
    else:
        return render_template('correct.html')

if __name__ == "__main__":
    app.run(debug=True, port=5003)
