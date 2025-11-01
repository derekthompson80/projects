from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
import json
import datetime

from pexels_api import PexelsAPI

# Initialize Pexels API with the provided key
PEXELS_API_KEY = "hSk5iMSAzF3dI68VVnjpil8CcXNd3twEdCZ4oTBl8ZrgP9ucJQQnwTLp"
pexels = PexelsAPI(PEXELS_API_KEY)

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
    """List files in the blog_entries directory.
    - Default: JSON with both .json and .txt files (name, size, modified)
    - If ?format=text: return a plain-text list (one per line) of only .txt filenames.
    """
    try:
        if not os.path.isdir(BLOG_ENTRIES_DIR):
            # Text format requested → return plain 404 message; otherwise JSON
            if request.args.get('format') == 'text':
                return ("blog_entries directory not found\n", 404, {'Content-Type': 'text/plain; charset=utf-8'})
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

        # Plain text mode: return only .txt filenames, one per line
        if request.args.get('format') == 'text':
            txt_names = [f['name'] for f in files if f['name'].lower().endswith('.txt')]
            body = "\n".join(txt_names) + ("\n" if txt_names else "")
            return (body, 200, {'Content-Type': 'text/plain; charset=utf-8'})

        # Default JSON
        return jsonify({'files': files})
    except Exception as e:
        app.logger.error(f"Error listing blog entry files: {e}")
        if request.args.get('format') == 'text':
            return (f"Error: {str(e)}\n", 500, {'Content-Type': 'text/plain; charset=utf-8'})
        return jsonify({'error': str(e)}), 500


def _parse_txt_entry(file_path: str, entry_id: str) -> dict:
    """Parse a legacy .txt blog entry file into a structured dict.
    Expected header lines at top (any order), then a blank line, then content:
      Title: ...
      Author: ...
      Date: YYYY-MM-DD HH:MM:SS (free-form kept as-is)
    The rest of the file is the content body.
    """
    title = 'Untitled'
    author = 'Anonymous'
    date = ''
    content_lines: list[str] = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Extract simple headers from the first ~20 lines or until first non-header content
        i = 0
        max_header_scan = min(len(lines), 20)
        while i < max_header_scan:
            line = lines[i].rstrip('\n')
            if not line.strip():
                # Allow a blank separator; continue scanning a bit further
                i += 1
                # Stop scanning headers if we already saw some headers and hit a blank line
                if (title != 'Untitled' or author != 'Anonymous' or date):
                    break
                continue
            low = line.lower()
            if low.startswith('title:'):
                title = line.split(':', 1)[1].strip() or title
            elif low.startswith('author:'):
                author = line.split(':', 1)[1].strip() or author
            elif low.startswith('date:'):
                date = line.split(':', 1)[1].strip() or date
            else:
                # Not a header-like line; stop header scanning
                break
            i += 1
        # The rest is content
        content_lines = [l.rstrip('\n') for l in lines[i:]]
    except Exception:
        # On any failure, return minimal information
        content_lines = []
    content = '\n'.join(content_lines).strip('\n')
    return {
        'id': entry_id,
        'title': title,
        'author': author,
        'date': date,
        'content': content,
    }


@app.route('/blog/entry/txt/<path:name>')
def blog_entry_txt(name: str):
    """Return a legacy .txt blog entry from blog_entries as plain text.
    Usage examples:
      /blog/entry/txt/20250613_171359_June_9__2025_75th
      /blog/entry/txt/20250613_171359_June_9__2025_75th.txt
    The response is returned as plain text content.
    """
    try:
        # Normalize filename and ensure .txt extension is allowed
        orig_name = name
        if not orig_name.lower().endswith('.txt'):
            filename = f"{orig_name}.txt"
        else:
            filename = orig_name

        # Resolve path inside BLOG_ENTRIES_DIR only
        candidate = os.path.normpath(os.path.join(BLOG_ENTRIES_DIR, filename))
        base_dir = os.path.normpath(BLOG_ENTRIES_DIR)
        if not candidate.startswith(base_dir):
            return "Invalid path", 400
        if not os.path.isfile(candidate):
            return "File not found", 404

        # Read and return the raw file content as plain text
        with open(candidate, 'r', encoding='utf-8') as f:
            content = f.read()
        
        from flask import Response
        return Response(content, mimetype='text/plain')
    except Exception as e:
        app.logger.error(f"Error reading txt entry '{name}': {e}")
        return f"Error: {str(e)}", 500


@app.route('/blog/entries/browse')
def browse_entry_files():
    """Render an HTML page to browse and open .txt files in blog_entries.
    - Lists only .txt files
    - Sorted by last modified (desc)
    - Each filename links to the plain-text endpoint `/blog/entry/txt/<name>`
    """
    try:
        if not os.path.isdir(BLOG_ENTRIES_DIR):
            # Render a friendly empty state
            return render_template('entries_browse.html', files=[], error='blog_entries directory not found')

        files = []
        for name in os.listdir(BLOG_ENTRIES_DIR):
            if not name.lower().endswith('.txt'):
                continue
            path = os.path.join(BLOG_ENTRIES_DIR, name)
            try:
                files.append({
                    'name': name,
                    'size': os.path.getsize(path),
                    'modified': datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S'),
                })
            except Exception:
                # Skip files that cannot be stat'ed
                continue

        # Sort by modified desc
        try:
            files.sort(key=lambda x: x['modified'], reverse=True)
        except Exception:
            pass

        return render_template('entries_browse.html', files=files, error=None)
    except Exception as e:
        app.logger.error(f"Error rendering entries browse page: {e}")
        return render_template('entries_browse.html', files=[], error=str(e)), 500


def _comments_count(entry_id: str) -> int:
    """Return number of comments for an entry based on blog_comments/<entry_id>.json."""
    try:
        path = os.path.join(COMMENTS_DIR, f"{entry_id}.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                comments = json.load(f)
                return len(comments) if isinstance(comments, list) else 0
    except Exception:
        return 0
    return 0


@app.route('/blog/entries/db')
def entries_db():
    """Render an HTML page that lists entries fetched from the database layer."""
    # Load from DB layer
    try:
        try:
            from .blog_db import get_entries, init_schema
        except ImportError:
            from blog_db import get_entries, init_schema
        try:
            init_schema()
        except Exception as e:
            app.logger.error(f"DB schema init failed: {e}")
        items = []
        for e in get_entries():
            items.append({
                'id': e['id'],
                'title': e.get('title') or 'Untitled',
                'author': e.get('author') or 'Anonymous',
                'date': e.get('date') or '',
                'comments_count': _comments_count(e['id']),
            })
        return render_template('entries_db.html', entries=items, error=None)
    except Exception as ex:
        app.logger.error(f"Failed to load DB entries: {ex}")
        return render_template('entries_db.html', entries=[], error=str(ex)), 500


@app.route('/blog/entries/db.json')
def entries_db_json():
    """Return DB entries as JSON (normalized) with comments_count."""
    try:
        try:
            from .blog_db import get_entries, init_schema
        except ImportError:
            from blog_db import get_entries, init_schema
        try:
            init_schema()
        except Exception as e:
            app.logger.error(f"DB schema init failed: {e}")
        items = []
        for e in get_entries():
            items.append({
                'id': e['id'],
                'title': e.get('title') or 'Untitled',
                'author': e.get('author') or 'Anonymous',
                'date': e.get('date') or '',
                'comments_count': _comments_count(e['id']),
            })
        return jsonify({'entries': items})
    except Exception as ex:
        app.logger.error(f"Failed to load DB entries (json): {ex}")
        return jsonify({'entries': [], 'error': str(ex)}), 500


if __name__ == '__main__':
    app.run(debug=True)
