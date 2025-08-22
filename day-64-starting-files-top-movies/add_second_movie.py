from main import app, db, Movie

# Create the second movie with the provided details
second_movie = Movie(
    title="Avatar The Way of Water",
    year=2022,
    description="Set more than a decade after the events of the first film, learn the story of the Sully family (Jake, Neytiri, and their kids), the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
    rating=7.3,
    ranking=9,
    review="I liked the water.",
    img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
)

# Add the movie to the database within the application context
with app.app_context():
    # Check if a movie with this title already exists
    existing_movie = db.session.execute(db.select(Movie).filter_by(title="Avatar The Way of Water")).scalar()
    
    if existing_movie:
        print(f"A movie with the title '{second_movie.title}' already exists in the database.")
        print("Updating the existing movie with the new details...")
        
        # Update the existing movie with the new details
        existing_movie.description = second_movie.description
        existing_movie.year = second_movie.year
        existing_movie.rating = second_movie.rating
        existing_movie.ranking = second_movie.ranking
        existing_movie.review = second_movie.review
        existing_movie.img_url = second_movie.img_url
    else:
        # Add the new movie to the database
        print(f"Adding new movie: {second_movie.title}")
        db.session.add(second_movie)
    
    # Commit the changes
    db.session.commit()
    print("Database updated successfully!")
    
    # Print all movies in the database
    result = db.session.execute(db.select(Movie))
    all_movies = result.scalars().all()
    print("\nMovies in the database:")
    for movie in all_movies:
        print(f"- {movie.title} ({movie.year}): {movie.rating}/10")