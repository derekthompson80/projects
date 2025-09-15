from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
import tempfile
import json
import datetime
from werkzeug.utils import secure_filename

# Import the txt.reviewer functionality
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Import with the correct module name (txt.reviewer.py -> txt_reviewer)
from txt_reviewer import correct_text, write_txt, process_document, process_blog_entry, save_blog_entry
from pexels_api import PexelsAPI

# Initialize Pexels API with the provided key
PEXELS_API_KEY = "hSk5iMSAzF3dI68VVnjpil8CcXNd3twEdCZ4oTBl8ZrgP9ucJQQnwTLp"
pexels = PexelsAPI(PEXELS_API_KEY)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

@app.before_request
def redirect_to_pythonanywhere():
    """Redirect all requests to spade605.pythonanywhere.com"""
    # Allow local development/testing without redirect
    if app.debug or app.testing or os.environ.get('DISABLE_PROD_REDIRECT', '').lower() in ('1', 'true', 'yes'):
        return None

    # Only redirect if host is not already the target domain
    if request.host != 'spade605.pythonanywhere.com':
        # Construct the new URL with the same path and query parameters
        target_url = f"https://spade605.pythonanywhere.com{request.full_path}"
        return redirect(target_url, code=301)  # 301 is permanent redirect

# Blog configuration
BLOG_ENTRIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog_entries')
COMMENTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog_comments')
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# Create directories if they don't exist
os.makedirs(BLOG_ENTRIES_DIR, exist_ok=True)
os.makedirs(COMMENTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure upload settings
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
ALLOWED_EXTENSIONS = {'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return redirect(url_for('blog'))

# New explicit route for grammar checker
@app.route('/grammar')
def grammar():
    """Explicit route path for the grammar checker UI"""
    return render_template('index.html')

# New explicit route for blog homepage path alias
@app.route('/blog-home')
def blog_home():
    """Alias path that routes to the blog homepage"""
    return redirect(url_for('blog'))

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    # Check if the file is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Check if the file is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload a .docx file'}), 400

    # Save the file temporarily
    filename = secure_filename(file.filename)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(temp_path)

    # Process the document
    output_filename = f"corrected_{filename.rsplit('.', 1)[0]}.txt"
    output_path = os.path.join(tempfile.gettempdir(), output_filename)

    try:
        process_document(temp_path, output_path)

        # Read the corrected text
        with open(output_path, 'r', encoding='utf-8') as f:
            corrected_text = f.read()

        # Clean up temporary files
        os.unlink(temp_path)
        os.unlink(output_path)

        return jsonify({
            'success': True,
            'document_name': filename.rsplit('.', 1)[0],
            'corrected_text': corrected_text
        })
    except Exception as e:
        # Clean up temporary files if they exist
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        if os.path.exists(output_path):
            os.unlink(output_path)

        return jsonify({'error': str(e)}), 500




@app.route('/pexels/search')
def pexels_search():
    """Handle Pexels API search requests"""
    query = request.args.get('query', '')
    media_type = request.args.get('type', 'photos')

    if not query:
        return jsonify({'error': 'Query parameter is required'}), 400

    try:
        if media_type == 'photos':
            results = pexels.search_photos(query)
        else:
            results = pexels.search_videos(query)

        return jsonify(results)
    except Exception as e:
        app.logger.error(f"Error searching Pexels API: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Blog routes
@app.route('/blog')
def blog():
    """Display the blog homepage with a list of entries"""
    # Load from database
    try:
        from .blog_db import get_entries, init_schema
    except ImportError:
        from blog_db import get_entries, init_schema

    # Ensure schema exists
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed: {e}")

    entries = []
    try:
        db_entries = get_entries()
        for e in db_entries:
            content_preview = e['content'][:200] + '...' if len(e['content']) > 200 else e['content']
            # Count comments from filesystem for now to avoid changing comments storage
            comments_count = 0
            # Comments still tied to filename; use entry id as key
            possible_json = os.path.join(COMMENTS_DIR, f"{e['id']}.json")
            if os.path.exists(possible_json):
                try:
                    with open(possible_json, 'r', encoding='utf-8') as cf:
                        comments = json.load(cf)
                        comments_count = len(comments)
                except Exception:
                    comments_count = 0

            entries.append({
                'id': e['id'],
                'title': e['title'],
                'author': e['author'],
                'date': e['date'],
                'content': content_preview,
                'comments_count': comments_count,
                'media': e.get('media')
            })
    except Exception as ex:
        app.logger.error(f"Failed to load entries from DB: {ex}")

    return render_template('blog.html', entries=entries)

@app.route('/blog/entry/<entry_id>')
def view_entry(entry_id):
    """Display a single blog entry with its comments"""
    # Load entry from database
    try:
        from .blog_db import get_entry, init_schema
    except ImportError:
        from blog_db import get_entry, init_schema
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed: {e}")

    entry = get_entry(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    # Get comments
    comments = []
    comment_file = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
    if os.path.exists(comment_file):
        try:
            with open(comment_file, 'r', encoding='utf-8') as cf:
                comments = json.load(cf)
        except Exception:
            comments = []

    return render_template('entry.html', 
                         entry=entry, 
                         comments=comments)

@app.route('/blog/new', methods=['GET', 'POST'])
def new_entry():
    """Create a new blog entry"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        author = request.form.get('author', '').strip() or 'Anonymous'

        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('new_entry.html', 
                                  title=title, 
                                  content=content, 
                                  author=author)

        try:
            # Check if this is a confirmation of grammar changes
            if request.form.get('confirm_changes') == 'true':
                # Use the corrected versions from the form
                corrected_title = request.form.get('corrected_title', title)
                corrected_content = request.form.get('corrected_content', content)
            else:
                # Process the entry with grammar checking
                corrected_title, corrected_content = process_blog_entry(title, content)

                # If there are changes, show the confirmation screen
                if corrected_title != title or corrected_content != content:
                    # Get media information if provided
                    media = None
                    if request.form.get('media_id'):
                        media = {
                            'id': request.form.get('media_id'),
                            'type': request.form.get('media_type'),
                            'url': request.form.get('media_url'),
                            'thumbnail': request.form.get('media_thumbnail'),
                            'width': request.form.get('media_width'),
                            'height': request.form.get('media_height'),
                            'attribution': request.form.get('media_attribution')
                        }

                    return render_template('confirm_changes.html',
                                          original_title=title,
                                          original_content=content,
                                          corrected_title=corrected_title,
                                          corrected_content=corrected_content,
                                          author=author,
                                          media=media,
                                          is_new=True)

            # Get media information if provided
            media = None
            if request.form.get('media_id'):
                media = {
                    'id': request.form.get('media_id'),
                    'type': request.form.get('media_type'),
                    'url': request.form.get('media_url'),
                    'thumbnail': request.form.get('media_thumbnail'),
                    'width': request.form.get('media_width'),
                    'height': request.form.get('media_height'),
                    'attribution': request.form.get('media_attribution')
                }

            # Save the entry to database
            try:
                from .blog_db import insert_entry, init_schema
            except ImportError:
                from blog_db import insert_entry, init_schema
            try:
                init_schema()
            except Exception as e:
                app.logger.error(f"DB schema init failed: {e}")

            entry_id = insert_entry(corrected_title, corrected_content, author, media)

            flash('Blog entry created successfully', 'success')
            return redirect(url_for('view_entry', entry_id=entry_id))
        except Exception as e:
            app.logger.error(f"Error creating blog entry: {str(e)}")
            flash('An error occurred while creating the blog entry. Please try again.', 'error')
            return render_template('new_entry.html', 
                                  title=title, 
                                  content=content, 
                                  author=author)

    return render_template('new_entry.html')

@app.route('/blog/entry/<entry_id>/edit', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """Edit an existing blog entry"""
    # Load from DB
    try:
        from .blog_db import get_entry, update_entry, init_schema
    except ImportError:
        from blog_db import get_entry, update_entry, init_schema
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed: {e}")

    entry = get_entry(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    title = entry['title']
    author = entry['author']
    date_str = entry['date']
    media = entry.get('media')
    entry_content = entry['content']

    if request.method == 'POST':
        # Get form data
        new_title = request.form.get('title', '').strip()
        new_content = request.form.get('content', '').strip()
        new_author = request.form.get('author', '').strip() or author

        if not new_title or not new_content:
            flash('Title and content are required', 'error')
            return render_template('new_entry.html', 
                                  title=new_title, 
                                  content=new_content, 
                                  author=new_author,
                                  is_edit=True,
                                  entry_id=entry_id,
                                  media=media)

        try:
            # Check if this is a confirmation of grammar changes
            if request.form.get('confirm_changes') == 'true':
                # Use the corrected versions from the form
                corrected_title = request.form.get('corrected_title', new_title)
                corrected_content = request.form.get('corrected_content', new_content)
            else:
                # Process the entry with grammar checking
                corrected_title, corrected_content = process_blog_entry(new_title, new_content)

                # If there are changes, show the confirmation screen
                if corrected_title != new_title or corrected_content != new_content:
                    # Get media information if provided
                    new_media = None
                    if request.form.get('media_id'):
                        new_media = {
                            'id': request.form.get('media_id'),
                            'type': request.form.get('media_type'),
                            'url': request.form.get('media_url'),
                            'thumbnail': request.form.get('media_thumbnail'),
                            'width': request.form.get('media_width'),
                            'height': request.form.get('media_height'),
                            'attribution': request.form.get('media_attribution')
                        }
                    else:
                        new_media = media

                    return render_template('confirm_changes.html',
                                          original_title=new_title,
                                          original_content=new_content,
                                          corrected_title=corrected_title,
                                          corrected_content=corrected_content,
                                          author=new_author,
                                          media=new_media,
                                          is_new=False,
                                          entry_id=entry_id)

            # Get media information if provided
            new_media = None
            if request.form.get('media_id'):
                new_media = {
                    'id': request.form.get('media_id'),
                    'type': request.form.get('media_type'),
                    'url': request.form.get('media_url'),
                    'thumbnail': request.form.get('media_thumbnail'),
                    'width': request.form.get('media_width'),
                    'height': request.form.get('media_height'),
                    'attribution': request.form.get('media_attribution')
                }
            else:
                new_media = media

            # Save the updated entry in DB (entry_id remains the same)
            updated = update_entry(entry_id, corrected_title, corrected_content, new_author, new_media)
            if not updated:
                flash('Failed to update entry', 'error')
                return render_template('new_entry.html', 
                                      title=new_title, 
                                      content=new_content, 
                                      author=new_author,
                                      is_edit=True,
                                      entry_id=entry_id,
                                      media=new_media)

            flash('Blog entry updated successfully', 'success')
            return redirect(url_for('view_entry', entry_id=entry_id))
        except Exception as e:
            app.logger.error(f"Error updating blog entry: {str(e)}")
            flash('An error occurred while updating the blog entry. Please try again.', 'error')
            return render_template('new_entry.html', 
                                  title=new_title, 
                                  content=new_content, 
                                  author=new_author,
                                  is_edit=True,
                                  entry_id=entry_id,
                                  media=media)

    # GET request - show the edit form
    return render_template('new_entry.html', 
                          title=title, 
                          content=entry_content, 
                          author=author,
                          is_edit=True,
                          entry_id=entry_id,
                          media=media)

@app.route('/blog/entry/<entry_id>/delete', methods=['POST'])
def delete_entry(entry_id):
    """Delete a blog entry and its comments"""
    # Delete from DB
    try:
        from .blog_db import delete_entry as db_delete_entry, init_schema
    except ImportError:
        from blog_db import delete_entry as db_delete_entry, init_schema
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed: {e}")

    try:
        deleted = db_delete_entry(entry_id)
        if not deleted:
            flash('Entry not found', 'error')
            return redirect(url_for('blog'))

        # Delete the comments file if it exists
        comment_file = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
        if os.path.exists(comment_file):
            os.remove(comment_file)

        flash('Blog entry deleted successfully', 'success')
        return redirect(url_for('blog'))
    except Exception as e:
        app.logger.error(f"Error deleting blog entry: {str(e)}")
        flash('An error occurred while deleting the blog entry. Please try again.', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))

@app.route('/blog/entry/<entry_id>/comment', methods=['POST'])
def add_comment(entry_id):
    """Add a comment to a blog entry"""
    # Verify entry exists in DB
    try:
        from .blog_db import get_entry, init_schema
    except ImportError:
        from blog_db import get_entry, init_schema
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed: {e}")
    entry = get_entry(entry_id)
    if not entry:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    # Get comment data
    author = request.form.get('author', '').strip() or 'Anonymous'
    content = request.form.get('content', '').strip()

    # Check if this is a confirmation of grammar changes
    if request.form.get('confirm_changes') == 'true':
        # Use the corrected version from the form
        corrected_content = request.form.get('corrected_content', content)
    else:
        # Regular comment submission
        if not content:
            flash('Comment content is required', 'error')
            return redirect(url_for('view_entry', entry_id=entry_id))

        try:
            # Process the comment with grammar checking
            corrected_content = correct_text(content)

            # If there are changes, show the confirmation screen
            if corrected_content != content:
                # Build entry info from DB
                title = entry['title']
                entry_author = entry['author']
                date_str = entry['date']
                media = entry.get('media')
                entry_content_text = entry['content']

                # Get comments
                comments = []
                comment_file = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
                if os.path.exists(comment_file):
                    with open(comment_file, 'r', encoding='utf-8') as cf:
                        comments = json.load(cf)

                # Render the confirmation template for comments
                return render_template('confirm_comment.html',
                                      entry={
                                          'id': entry_id,
                                          'title': title,
                                          'author': entry_author,
                                          'date': date_str,
                                          'content': entry_content_text,
                                          'media': media
                                      },
                                      comments=comments,
                                      original_content=content,
                                      corrected_content=corrected_content,
                                      author=author)

        except Exception as e:
            app.logger.error(f"Error processing comment: {str(e)}")
            flash('An error occurred while processing the comment. Please try again.', 'error')
            return redirect(url_for('view_entry', entry_id=entry_id))

    try:
        # Create comment object
        comment = {
            'author': author,
            'content': corrected_content,
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save the comment JSON keyed by entry_id
        comment_file = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
        comments = []

        if os.path.exists(comment_file):
            with open(comment_file, 'r', encoding='utf-8') as f:
                comments = json.load(f)

        comments.append(comment)

        with open(comment_file, 'w', encoding='utf-8') as f:
            json.dump(comments, f, indent=2)

        flash('Comment added successfully', 'success')
        return redirect(url_for('view_entry', entry_id=entry_id))
    except Exception as e:
        app.logger.error(f"Error adding comment: {str(e)}")
        flash('An error occurred while adding the comment. Please try again.', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))

if __name__ == '__main__':
    app.run(debug=True)
