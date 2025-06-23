from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import tempfile
import json
import datetime
import io
import requests
from werkzeug.utils import secure_filename

# Import the txt.reviewer functionality
import sys
import os
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
    # Skip redirection if request is already to the target domain
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
    return render_template('index.html')

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

@app.route('/home')
def home():
    """Redirect to the blog homepage"""
    return redirect(url_for('blog'))


@app.route('/logout')
def logout():
    # Clear the session
    session.clear()
    return redirect(url_for('index'))

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
    entries = []

    # Get all blog entries
    if os.path.exists(BLOG_ENTRIES_DIR):
        for filename in sorted(os.listdir(BLOG_ENTRIES_DIR), reverse=True):
            if filename.endswith('.txt'):
                filepath = os.path.join(BLOG_ENTRIES_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse the entry metadata
                lines = content.split('\n')
                title = lines[0].replace('Title: ', '') if lines and lines[0].startswith('Title: ') else 'Untitled'
                author = lines[1].replace('Author: ', '') if len(lines) > 1 and lines[1].startswith('Author: ') else 'Anonymous'
                date_str = lines[2].replace('Date: ', '') if len(lines) > 2 and lines[2].startswith('Date: ') else ''

                # Parse media information if available
                media = None
                line_index = 3
                if len(lines) > line_index and lines[line_index].startswith('Media-ID:'):
                    media = {
                        'id': lines[line_index].replace('Media-ID: ', ''),
                        'type': lines[line_index + 1].replace('Media-Type: ', '') if len(lines) > line_index + 1 else '',
                        'url': lines[line_index + 2].replace('Media-URL: ', '') if len(lines) > line_index + 2 else '',
                        'thumbnail': lines[line_index + 3].replace('Media-Thumbnail: ', '') if len(lines) > line_index + 3 else '',
                        'width': lines[line_index + 4].replace('Media-Width: ', '') if len(lines) > line_index + 4 else '',
                        'height': lines[line_index + 5].replace('Media-Height: ', '') if len(lines) > line_index + 5 else '',
                        'attribution': lines[line_index + 6].replace('Media-Attribution: ', '') if len(lines) > line_index + 6 else ''
                    }
                    # Skip media metadata lines to get to content
                    line_index += 7

                # Get the entry content (everything after the metadata)
                content_start_index = line_index + 1  # Skip the empty line after metadata
                entry_content = '\n'.join(lines[content_start_index:]) if len(lines) > content_start_index else ''

                # Get comments count
                comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(filename)[0]}.json")
                comments_count = 0
                if os.path.exists(comment_file):
                    with open(comment_file, 'r', encoding='utf-8') as cf:
                        comments = json.load(cf)
                        comments_count = len(comments)

                entries.append({
                    'id': os.path.splitext(filename)[0],
                    'title': title,
                    'author': author,
                    'date': date_str,
                    'content': entry_content[:200] + '...' if len(entry_content) > 200 else entry_content,
                    'comments_count': comments_count,
                    'media': media
                })

    return render_template('blog.html', entries=entries)

@app.route('/blog/entry/<entry_id>')
def view_entry(entry_id):
    """Display a single blog entry with its comments"""
    # Find the entry file
    entry_file = None
    for filename in os.listdir(BLOG_ENTRIES_DIR):
        if filename.startswith(entry_id) and filename.endswith('.txt'):
            entry_file = os.path.join(BLOG_ENTRIES_DIR, filename)
            break

    if not entry_file:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    # Read the entry
    with open(entry_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the entry metadata
    lines = content.split('\n')
    title = lines[0].replace('Title: ', '') if lines and lines[0].startswith('Title: ') else 'Untitled'
    author = lines[1].replace('Author: ', '') if len(lines) > 1 and lines[1].startswith('Author: ') else 'Anonymous'
    date_str = lines[2].replace('Date: ', '') if len(lines) > 2 and lines[2].startswith('Date: ') else ''

    # Parse media information if available
    media = None
    line_index = 3
    if len(lines) > line_index and lines[line_index].startswith('Media-ID:'):
        media = {
            'id': lines[line_index].replace('Media-ID: ', ''),
            'type': lines[line_index + 1].replace('Media-Type: ', '') if len(lines) > line_index + 1 else '',
            'url': lines[line_index + 2].replace('Media-URL: ', '') if len(lines) > line_index + 2 else '',
            'thumbnail': lines[line_index + 3].replace('Media-Thumbnail: ', '') if len(lines) > line_index + 3 else '',
            'width': lines[line_index + 4].replace('Media-Width: ', '') if len(lines) > line_index + 4 else '',
            'height': lines[line_index + 5].replace('Media-Height: ', '') if len(lines) > line_index + 5 else '',
            'attribution': lines[line_index + 6].replace('Media-Attribution: ', '') if len(lines) > line_index + 6 else ''
        }
        # Skip media metadata lines to get to content
        line_index += 7

    # Get the entry content (everything after the metadata)
    content_start_index = line_index + 1  # Skip the empty line after metadata
    entry_content = '\n'.join(lines[content_start_index:]) if len(lines) > content_start_index else ''

    # Get comments
    comments = []
    # Find the actual filename that starts with entry_id
    for filename in os.listdir(BLOG_ENTRIES_DIR):
        if filename.startswith(entry_id) and filename.endswith('.txt'):
            comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(filename)[0]}.json")
            if os.path.exists(comment_file):
                with open(comment_file, 'r', encoding='utf-8') as cf:
                    comments = json.load(cf)
            break

    return render_template('entry.html', 
                          entry={
                              'id': entry_id,
                              'title': title,
                              'author': author,
                              'date': date_str,
                              'content': entry_content,
                              'media': media
                          }, 
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

            # Save the entry with media information
            file_path = save_blog_entry(corrected_title, corrected_content, author, media, BLOG_ENTRIES_DIR)

            # Get the entry ID from the filename
            entry_id = os.path.splitext(os.path.basename(file_path))[0]

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
    # Find the entry file
    entry_file = None
    for filename in os.listdir(BLOG_ENTRIES_DIR):
        if filename.startswith(entry_id) and filename.endswith('.txt'):
            entry_file = os.path.join(BLOG_ENTRIES_DIR, filename)
            break

    if not entry_file:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    # Read the entry
    with open(entry_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Parse the entry metadata
    lines = content.split('\n')
    title = lines[0].replace('Title: ', '') if lines and lines[0].startswith('Title: ') else 'Untitled'
    author = lines[1].replace('Author: ', '') if len(lines) > 1 and lines[1].startswith('Author: ') else 'Anonymous'
    date_str = lines[2].replace('Date: ', '') if len(lines) > 2 and lines[2].startswith('Date: ') else ''

    # Parse media information if available
    media = None
    line_index = 3
    if len(lines) > line_index and lines[line_index].startswith('Media-ID:'):
        media = {
            'id': lines[line_index].replace('Media-ID: ', ''),
            'type': lines[line_index + 1].replace('Media-Type: ', '') if len(lines) > line_index + 1 else '',
            'url': lines[line_index + 2].replace('Media-URL: ', '') if len(lines) > line_index + 2 else '',
            'thumbnail': lines[line_index + 3].replace('Media-Thumbnail: ', '') if len(lines) > line_index + 3 else '',
            'width': lines[line_index + 4].replace('Media-Width: ', '') if len(lines) > line_index + 4 else '',
            'height': lines[line_index + 5].replace('Media-Height: ', '') if len(lines) > line_index + 5 else '',
            'attribution': lines[line_index + 6].replace('Media-Attribution: ', '') if len(lines) > line_index + 6 else ''
        }
        # Skip media metadata lines to get to content
        line_index += 7

    # Get the entry content (everything after the metadata)
    content_start_index = line_index + 1  # Skip the empty line after metadata
    entry_content = '\n'.join(lines[content_start_index:]) if len(lines) > content_start_index else ''

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

            # Save the updated entry
            # First, delete the old file
            os.remove(entry_file)

            # Then save the new entry with the same ID prefix
            timestamp = entry_id.split('_')[0]
            safe_title = "".join(c if c.isalnum() else "_" for c in corrected_title)
            filename = f"{timestamp}_{safe_title}.txt"
            file_path = os.path.join(BLOG_ENTRIES_DIR, filename)

            # Format the blog entry
            entry_text = f"Title: {corrected_title}\n"
            entry_text += f"Author: {new_author}\n"
            entry_text += f"Date: {date_str}\n"  # Keep the original date

            # Add media information if provided
            if new_media and new_media.get('id'):
                entry_text += f"Media-ID: {new_media.get('id', '')}\n"
                entry_text += f"Media-Type: {new_media.get('type', '')}\n"
                entry_text += f"Media-URL: {new_media.get('url', '')}\n"
                entry_text += f"Media-Thumbnail: {new_media.get('thumbnail', '')}\n"
                entry_text += f"Media-Width: {new_media.get('width', '')}\n"
                entry_text += f"Media-Height: {new_media.get('height', '')}\n"
                entry_text += f"Media-Attribution: {new_media.get('attribution', '')}\n"

            entry_text += f"\n{corrected_content}\n"

            # Write to file
            write_txt(file_path, entry_text)

            # Update the comments file if it exists
            comment_file = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
            if os.path.exists(comment_file):
                new_comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(filename)[0]}.json")
                os.rename(comment_file, new_comment_file)

            flash('Blog entry updated successfully', 'success')
            return redirect(url_for('view_entry', entry_id=os.path.splitext(os.path.basename(file_path))[0]))
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
    # Find the entry file
    entry_file = None
    for filename in os.listdir(BLOG_ENTRIES_DIR):
        if filename.startswith(entry_id) and filename.endswith('.txt'):
            entry_file = os.path.join(BLOG_ENTRIES_DIR, filename)
            break

    if not entry_file:
        flash('Entry not found', 'error')
        return redirect(url_for('blog'))

    try:
        # Delete the entry file
        os.remove(entry_file)

        # Get the actual filename without extension
        actual_filename = os.path.basename(entry_file)

        # Delete the comments file if it exists
        comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(actual_filename)[0]}.json")
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
    # Find the entry file to make sure it exists
    entry_exists = False
    entry_file = None
    for filename in os.listdir(BLOG_ENTRIES_DIR):
        if filename.startswith(entry_id) and filename.endswith('.txt'):
            entry_exists = True
            entry_file = os.path.join(BLOG_ENTRIES_DIR, filename)
            break

    if not entry_exists:
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
                # Read the entry to display it in the confirmation screen
                with open(entry_file, 'r', encoding='utf-8') as f:
                    entry_content = f.read()

                # Parse the entry metadata
                lines = entry_content.split('\n')
                title = lines[0].replace('Title: ', '') if lines and lines[0].startswith('Title: ') else 'Untitled'
                entry_author = lines[1].replace('Author: ', '') if len(lines) > 1 and lines[1].startswith('Author: ') else 'Anonymous'
                date_str = lines[2].replace('Date: ', '') if len(lines) > 2 and lines[2].startswith('Date: ') else ''

                # Parse media information if available
                media = None
                line_index = 3
                if len(lines) > line_index and lines[line_index].startswith('Media-ID:'):
                    media = {
                        'id': lines[line_index].replace('Media-ID: ', ''),
                        'type': lines[line_index + 1].replace('Media-Type: ', '') if len(lines) > line_index + 1 else '',
                        'url': lines[line_index + 2].replace('Media-URL: ', '') if len(lines) > line_index + 2 else '',
                        'thumbnail': lines[line_index + 3].replace('Media-Thumbnail: ', '') if len(lines) > line_index + 3 else '',
                        'width': lines[line_index + 4].replace('Media-Width: ', '') if len(lines) > line_index + 4 else '',
                        'height': lines[line_index + 5].replace('Media-Height: ', '') if len(lines) > line_index + 5 else '',
                        'attribution': lines[line_index + 6].replace('Media-Attribution: ', '') if len(lines) > line_index + 6 else ''
                    }
                    # Skip media metadata lines to get to content
                    line_index += 7

                # Get the entry content (everything after the metadata)
                content_start_index = line_index + 1  # Skip the empty line after metadata
                entry_content_text = '\n'.join(lines[content_start_index:]) if len(lines) > content_start_index else ''

                # Get comments
                comments = []
                comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(os.path.basename(entry_file))[0]}.json")
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

        # Save the comment
        # Find the actual filename that starts with entry_id
        actual_filename = None
        for filename in os.listdir(BLOG_ENTRIES_DIR):
            if filename.startswith(entry_id) and filename.endswith('.txt'):
                actual_filename = filename
                break

        if not actual_filename:
            flash('Entry not found', 'error')
            return redirect(url_for('blog'))

        comment_file = os.path.join(COMMENTS_DIR, f"{os.path.splitext(actual_filename)[0]}.json")
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
