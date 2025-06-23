import movies

# Test the get_top_movies_by_genre function
genre_name = "Action"  # Example genre
year = "2023"  # Example year

# Get the genre ID using the get_genre_id function
genre_id = movies.get_genre_id(genre_name)
if not genre_id:
    print(f"Could not find genre ID for '{genre_name}'. Using default ID 28.")
    genre_id = 28  # Default ID for Action genre as fallback

print(f"Testing get_top_movies_by_genre with genre '{genre_name}' (ID: {genre_id}) and year '{year}'")
movies_list = movies.get_top_movies_by_genre(genre_id, year)

if movies_list:
    print(f"Success! Found {len(movies_list)} movies.")
    # Print the first movie as an example
    if len(movies_list) > 0:
        print(f"Example movie: {movies_list[0]['title']}")
else:
    print("No movies found or an error occurred.")
