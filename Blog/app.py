from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
import json
import datetime
import os
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore
import paramiko
import MySQLdb
import sshtunnel
from typing import Optional, Dict, Any, List

from pexels_api import PexelsAPI

# Load environment variables from .env located alongside this file
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# Initialize Pexels API with the provided key
pexels = PexelsAPI(os.getenv('PEXELS_API_KEY'))

# Grammar correction features removed: provide no-op stubs to keep routes simple
# and avoid any dependency on the old txt_reviewer module.
def correct_text(text: str) -> str:
    return text

def process_blog_entry(title: str, content: str) -> tuple[str, str]:
    return title, content

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

# Create directories if they don't exist
os.makedirs(BLOG_ENTRIES_DIR, exist_ok=True)
os.makedirs(COMMENTS_DIR, exist_ok=True)

@app.route('/')
def index():
    # Blog is the homepage
    return redirect(url_for('blog'))

# Grammar Checker features removed in Derek's Blog




def _client_ip() -> str:
    # Respect X-Forwarded-For if behind a proxy (e.g., PythonAnywhere)
    if 'X-Forwarded-For' in request.headers:
        return request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    return request.remote_addr or 'unknown'


@app.route('/grammar/login', methods=['GET', 'POST'])
def grammar_login():
    # Feature removed: redirect to blog home
    return redirect(url_for('blog'))


@app.route('/grammar/request-reset', methods=['GET', 'POST'])
def grammar_request_reset():
    # Feature removed: redirect to blog home
    return redirect(url_for('blog'))


@app.route('/grammar/reset/<token>')
def grammar_reset(token: str):
    # Feature removed: redirect to blog home
    return redirect(url_for('blog'))


@app.route('/grammar/logout')
def grammar_logout():
    # Feature removed: redirect to blog home
    return redirect(url_for('blog'))


# New explicit route for grammar checker (protected)
@app.route('/grammar')
def grammar():
    # Feature removed: redirect to blog home
    return redirect(url_for('blog'))

# New explicit route for blog homepage path alias
@app.route('/blog-home')
def blog_home():
    """Alias path that routes to the blog homepage"""
    return redirect(url_for('blog'))

@app.route('/upload', methods=['POST'])
def upload_file():
    # Feature removed as part of refactor to pure blog
    return jsonify({'error': 'Grammar upload/correction feature has been removed'}), 410




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

    def _load_entries_from_files() -> list[dict]:
        """Fallback: load entries from JSON files in BLOG_ENTRIES_DIR.
        Expected JSON structure: {id,title,author,date,content,media?} per file.
        Uses filename (without extension) as id if not present.
        """
        results: list[dict] = []
        try:
            if not os.path.isdir(BLOG_ENTRIES_DIR):
                return results
            for name in os.listdir(BLOG_ENTRIES_DIR):
                if not name.lower().endswith('.json'):
                    continue
                path = os.path.join(BLOG_ENTRIES_DIR, name)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        continue
                    entry_id = data.get('id') or os.path.splitext(name)[0]
                    title = data.get('title') or 'Untitled'
                    author = data.get('author') or 'Anonymous'
                    date = data.get('date') or ''
                    content = data.get('content') or ''
                    media = data.get('media') if isinstance(data.get('media'), dict) else None
                    # Count comments from filesystem (same as DB path does)
                    comments_count = 0
                    possible_json = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
                    if os.path.exists(possible_json):
                        try:
                            with open(possible_json, 'r', encoding='utf-8') as cf:
                                comments = json.load(cf)
                                if isinstance(comments, list):
                                    comments_count = len(comments)
                        except Exception:
                            comments_count = 0
                    # Preview like DB path does
                    content_preview = content[:200] + '...' if len(content) > 200 else content
                    results.append({
                        'id': entry_id,
                        'title': title,
                        'author': author,
                        'date': date,
                        'content': content_preview,
                        'comments_count': comments_count,
                        'media': media,
                    })
                except Exception:
                    # Skip malformed files
                    continue
            # Sort by date descending if possible
            try:
                from datetime import datetime
                def parse_dt(s: str):
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d_%H%M%S"):
                        try:
                            return datetime.strptime(s, fmt)
                        except Exception:
                            continue
                    return datetime.min
                results.sort(key=lambda e: parse_dt(e.get('date','')), reverse=True)
            except Exception:
                pass
        except Exception:
            pass
        return results

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

    entries: list[dict] = []
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
                        comments_count = len(comments) if isinstance(comments, list) else 0
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
        # If DB dependencies are missing, fall back to file-based entries without logging an error
        msg = str(ex)
        if isinstance(ex, RuntimeError) and 'Database dependencies are not installed' in msg:
            app.logger.info('DB deps missing; falling back to file-based entries in blog_entries directory.')
            entries = _load_entries_from_files()
        else:
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

    try:
        entry = get_entry(entry_id)
    except Exception as ex:
        # Fallback to file-based entry if DB deps missing
        if isinstance(ex, RuntimeError) and 'Database dependencies are not installed' in str(ex):
            path = os.path.join(BLOG_ENTRIES_DIR, f"{entry_id}.json")
            entry = None
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        entry = {
                            'id': entry_id,
                            'title': data.get('title') or 'Untitled',
                            'author': data.get('author') or 'Anonymous',
                            'date': data.get('date') or '',
                            'content': data.get('content') or '',
                            'media': data.get('media') if isinstance(data.get('media'), dict) else None,
                        }
            except Exception:
                entry = None
        else:
            raise
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
            # Grammar checker removed: use content as-is
            corrected_title = title
            corrected_content = content

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
            # Grammar checker removed: use content as-is
            corrected_title = new_title
            corrected_content = new_content

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

        # Delete the comment file if it exists
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

    # Grammar checker removed: save comment as-is
    if not content:
        flash('Comment content is required', 'error')
        return redirect(url_for('view_entry', entry_id=entry_id))

    corrected_content = content

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

@app.route('/blog/entries/files')
def list_entry_files():
    """List files in the blog_entries directory (JSON and TXT)."""
    try:
        if not os.path.isdir(BLOG_ENTRIES_DIR):
            return jsonify({'files': [], 'error': 'blog_entries directory not found'}), 404

        files = []
        for name in os.listdir(BLOG_ENTRIES_DIR):
            if name.lower().endswith(('.json', '.txt')):
                path = os.path.join(BLOG_ENTRIES_DIR, name)
                try:
                    info = {
                        'name': name,
                        'size': os.path.getsize(path),
                        'modified': datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    files.append(info)
                except Exception:
                    # If any single file fails to stat, skip it
                    continue

        # Sort by last modified (descending)
        try:
            files.sort(key=lambda x: x['modified'], reverse=True)
        except Exception:
            pass

        return jsonify({'files': files})
    except Exception as e:
        app.logger.error(f"Error listing blog entry files: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
