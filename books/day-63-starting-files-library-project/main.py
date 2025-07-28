from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from mysql.connector import Error

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt
python -m pip install mysql-connector-python

On MacOS type:
pip3 install -r requirements.txt
pip3 install mysql-connector-python

This will install the packages from requirements.txt for this project.
'''

# Database configuration
config = {
    'user': 'root',
    'password': 'Beholder30',
    'host': '127.0.0.1',
    'port': 3306,
    'raise_on_warnings': True
}

# Function to create database connection
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(**config)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return connection

# Initialize database and tables
def initialize_database():
    connection = create_connection()
    if connection:
        try:
            cursor = connection.cursor()
            
            # Create database if it doesn't exist
            cursor.execute("CREATE DATABASE IF NOT EXISTS books")
            cursor.execute("USE books")
            
            # Create books table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    author VARCHAR(255) NOT NULL,
                    rating FLOAT NOT NULL
                )
            """)
            
            connection.commit()
            print("Database and tables initialized successfully")
        except Error as e:
            print(f"Error initializing database: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

# Initialize the database when the app starts
initialize_database()

app = Flask(__name__)


@app.route('/')
def home():
    books = []
    connection = create_connection()
    if connection:
        try:
            connection.database = 'books'  # Select the books database
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM books")
            books = cursor.fetchall()
        except Error as e:
            print(f"Error fetching books: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
    return render_template('index.html', books=books)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        rating = request.form["rating"]
        
        connection = create_connection()
        if connection:
            try:
                connection.database = 'books'  # Select the books database
                cursor = connection.cursor()
                
                # Insert the new book into the database
                query = "INSERT INTO books (title, author, rating) VALUES (%s, %s, %s)"
                values = (title, author, rating)
                cursor.execute(query, values)
                
                connection.commit()
                print(f"Book '{title}' added successfully")
            except Error as e:
                print(f"Error adding book: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    
        return redirect(url_for('home'))
    return render_template('add.html')


if __name__ == "__main__":
    app.run(debug=True)

