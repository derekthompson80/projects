# Changes Summary - Adding Second Movie

## Task Completed
Successfully added a second movie to the database with the following details:

```python
second_movie = Movie(
    title="Avatar The Way of Water",
    year=2022,
    description="Set more than a decade after the events of the first film, learn the story of the Sully family (Jake, Neytiri, and their kids), the trouble that follows them, the lengths they go to keep each other safe, the battles they fight to stay alive, and the tragedies they endure.",
    rating=7.3,
    ranking=9,
    review="I liked the water.",
    img_url="https://image.tmdb.org/t/p/w500/t6HIqrRAclMCA60NsSmeqe9RmNV.jpg"
)
```

## Implementation Details
1. Created a script `add_second_movie.py` that:
   - Imports the necessary components from the main application
   - Creates a new Movie object with the provided details
   - Checks if a movie with the same title already exists
   - Adds the new movie to the database or updates an existing one
   - Commits the changes to the database
   - Displays all movies in the database

2. Executed the script, which successfully added the second movie to the database.

## Current Database State
The database now contains two movies:
- "Avatar: The Way of Water" (original sample movie)
- "Avatar The Way of Water" (newly added movie)

Both movies have similar details but slightly different titles and descriptions.

## Note
The application's home page will now display both movies, with rankings automatically adjusted based on the number of movies in the database.