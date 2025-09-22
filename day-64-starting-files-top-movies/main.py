from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float, Text
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, URL, NumberRange
import requests

'''
Red underlines? Install the required packages first: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap(app)

# CREATE DB
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CREATE TABLE
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

# Forms
class RateMovieForm(FlaskForm):
    rating = FloatField("Your Rating Out of 10 e.g. 7.5", validators=[DataRequired(), NumberRange(min=0, max=10)])
    review = TextAreaField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")

class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

class AddMovieForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    year = IntegerField("Year", validators=[DataRequired(), NumberRange(min=1900, max=2100)])
    description = TextAreaField("Description", validators=[DataRequired()])
    rating = FloatField("Rating", validators=[NumberRange(min=0, max=10)])
    ranking = IntegerField("Ranking", validators=[NumberRange(min=1)])
    review = TextAreaField("Review")
    img_url = StringField("Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Add Movie")

@app.route("/")
def home():
    # Get all movies from the database
    result = db.session.execute(db.select(Movie).order_by(Movie.ranking))
    all_movies = result.scalars().all()
    
    # If there are movies in the database, update their rankings
    if all_movies:
        for i in range(len(all_movies)):
            all_movies[i].ranking = len(all_movies) - i
        db.session.commit()
    
    return render_template("index.html", movies=all_movies)

@app.route("/add", methods=["GET", "POST"])
def add():
    form = FindMovieForm()
    if form.validate_on_submit():
        movie_title = form.title.data
        # API key from The Movie Database
        api_key = "1746088d2b0e9fe4217ab1a981d13858"
        # Search for movies with the given title
        search_url = f"https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": api_key,
            "query": movie_title
        }
        response = requests.get(search_url, params=params)
        data = response.json()
        movies = data.get("results", [])
        return render_template("select.html", movies=movies)
    return render_template("add.html", form=form)

@app.route("/find/<int:id>")
def find_movie(id):
    try:
        # API key from The Movie Database
        api_key = "1746088d2b0e9fe4217ab1a981d13858"
        # Get movie details from API
        movie_url = f"https://api.themoviedb.org/3/movie/{id}"
        params = {
            "api_key": api_key
        }
        response = requests.get(movie_url, params=params)
        
        # Check if the API request was successful
        if response.status_code != 200:
            app.logger.error(f"API request failed with status code {response.status_code}: {response.text}")
            return render_template("error.html", message=f"Failed to fetch movie details. Status code: {response.status_code}")
        
        movie_data = response.json()
        
        # Check if the movie data contains the required fields
        if not movie_data.get("title") or not movie_data.get("overview"):
            app.logger.error(f"Incomplete movie data received: {movie_data}")
            return render_template("error.html", message="Incomplete movie data received from the API.")
        
        # Create a new Movie object
        new_movie = Movie(
            title=movie_data["title"],
            year=int(movie_data["release_date"].split("-")[0]) if movie_data.get("release_date") else 0,
            description=movie_data["overview"],
            img_url=f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}" if movie_data.get("poster_path") else "",
            rating=0,
            ranking=0,
            review=""
        )
        
        # Add the new movie to the database
        db.session.add(new_movie)
        db.session.commit()
        
        # Redirect to edit page to add rating and review
        return redirect(url_for('edit', id=new_movie.id))
    
    except requests.RequestException as e:
        # Handle network-related errors
        app.logger.error(f"Network error when fetching movie data: {str(e)}")
        return render_template("error.html", message="Network error when fetching movie data. Please try again later.")
    
    except KeyError as e:
        # Handle missing keys in the API response
        app.logger.error(f"Missing key in API response: {str(e)}")
        return render_template("error.html", message="The movie data is incomplete or in an unexpected format.")
    
    except Exception as e:
        # Handle any other unexpected errors
        app.logger.error(f"Unexpected error in find_movie route: {str(e)}")
        return render_template("error.html", message="An unexpected error occurred. Please try again later.")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    movie = db.get_or_404(Movie, id)
    form = RateMovieForm()
    if form.validate_on_submit():
        movie.rating = form.rating.data
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie, form=form)

@app.route("/delete/<int:id>")
def delete(id):
    movie = db.get_or_404(Movie, id)
    db.session.delete(movie)
    db.session.commit()
    return redirect(url_for('home'))

# Add a sample movie to the database (for testing)
with app.app_context():
    # Check if the database is empty
    movie_count = db.session.execute(db.select(db.func.count(Movie.id))).scalar()
    if movie_count == 0:
        # Add a sample movie
        sample_movie = Movie(
            title="Avatar: The Way of Water",
            year=2022,
            description="Jake Sully lives with his newfound family formed on the extrasolar moon Pandora. Once a familiar threat returns to finish what was previously started, Jake must work with Neytiri and the army of the Na'vi race to protect their home.",
            rating=7.3,
            ranking=9,
            review="I liked the water.",
            img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
        )
        db.session.add(sample_movie)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
