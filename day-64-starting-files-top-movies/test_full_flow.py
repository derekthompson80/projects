import sys
import os

# Add the current directory to the path so we can import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to import the app and related objects from main.py
try:
    from main import app, db, Movie
    print("✓ Successfully imported app from main.py")
except ImportError as e:
    print(f"❌ Error importing from main.py: {e}")
    sys.exit(1)

def test_full_user_flow():
    """Test the full user flow from search to adding a movie"""
    print("\nTesting full user flow...")
    
    with app.test_client() as client:
        # Step 1: Visit the add page
        print("\nStep 1: Visiting /add page")
        response = client.get('/add')
        print(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Successfully loaded add page")
        else:
            print("❌ Failed to load add page")
            return
        
        # Step 2: Submit a search query
        print("\nStep 2: Submitting search query")
        
        # First get the page to extract the CSRF token
        response = client.get('/add')
        html = response.data.decode('utf-8')
        
        # Extract CSRF token
        import re
        csrf_token = None
        csrf_match = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html)
        if csrf_match:
            csrf_token = csrf_match.group(1)
            print(f"Found CSRF token: {csrf_token[:10]}...")
        else:
            print("❌ Could not find CSRF token")
            return
            
        search_data = {
            'title': 'Avatar',
            'submit': True,
            'csrf_token': csrf_token
        }
        response = client.post('/add', data=search_data, follow_redirects=False)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ Search results page loaded")
            # Check if the response contains movie links
            response_text = response.data.decode('utf-8')
            if 'Avatar' in response_text and 'href="/find/' in response_text:
                print("✓ Search results contain movie links")
            else:
                print("❌ Search results don't contain expected movie links")
                print("Response excerpt:", response_text[:500])
        else:
            print("❌ Failed to get search results")
            return
        
        # Step 3: Extract a movie ID from the response to simulate clicking on a movie
        import re
        movie_links = re.findall(r'href="(/find/\d+)"', response_text)
        
        if movie_links:
            movie_link = movie_links[0]
            movie_id = movie_link.split('/')[-1]
            print(f"Found movie link: {movie_link}")
            
            # Step 4: Visit the find_movie route
            print(f"\nStep 4: Visiting {movie_link}")
            response = client.get(movie_link, follow_redirects=False)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 302:
                print("✓ find_movie route returned a redirect")
                redirect_location = response.location
                print(f"Redirect location: {redirect_location}")
                
                # Step 5: Follow the redirect to the edit page
                print(f"\nStep 5: Following redirect to {redirect_location}")
                response = client.get(redirect_location, follow_redirects=False)
                print(f"Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    print("✓ Successfully loaded edit page")
                    response_text = response.data.decode('utf-8')
                    if 'Edit Movie Rating' in response_text:
                        print("✓ Edit page contains the expected content")
                    else:
                        print("❌ Edit page doesn't contain expected content")
                else:
                    print("❌ Failed to load edit page")
            else:
                print("❌ find_movie route did not return a redirect")
                print(f"Response data: {response.data.decode('utf-8')[:500]}")
        else:
            print("❌ Could not find any movie links in the search results")

if __name__ == "__main__":
    # Run the test
    with app.app_context():
        test_full_user_flow()