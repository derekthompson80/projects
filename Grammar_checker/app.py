from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
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
    # Open the Grammar Checker login screen first to ensure gatekeeping and tracking
    return redirect(url_for('grammar_login'))

# Grammar Checker authentication configuration
GRAMMAR_PASSWORD = 'Darklove90!'
FEATURE_NAME = 'grammar_checker'

# Email notification configuration
OWNER_EMAIL = os.environ.get('OWNER_EMAIL', 'spade605@gmail.com')
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'spade605@gmail.com')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', 'Darklove20!')


def _send_email(to_addr: str, subject: str, body: str) -> bool:
    # Email notifications disabled: suppress actual sending
    try:
        app.logger.info(
            f"Email notifications disabled. Suppressed email to {to_addr} with subject '{subject}'."
        )
    except Exception:
        # In case app.logger is not available for any reason, still succeed silently
        pass
    return True


def _client_ip() -> str:
    # Respect X-Forwarded-For if behind a proxy (e.g., PythonAnywhere)
    if 'X-Forwarded-For' in request.headers:
        return request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    return request.remote_addr or 'unknown'


@app.route('/grammar/login', methods=['GET', 'POST'])
def grammar_login():
    # Lazy import to avoid circulars and keep local dev flexible
    try:
        from .blog_db import (
            init_schema,
            log_auth_attempt,
            is_locked,
            get_consecutive_fail_count,
            create_reset_token,
        )
    except ImportError:
        from blog_db import (
            init_schema,
            log_auth_attempt,
            is_locked,
            get_consecutive_fail_count,
            create_reset_token,
        )

    # Ensure schema includes auth_attempts
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed on login: {e}")

    locked, until = (False, None)
    try:
        locked, until = is_locked(FEATURE_NAME)
    except Exception as e:
        app.logger.error(f"Lock check failed: {e}")

    if request.method == 'POST':
        if locked:
            flash(f"Grammar Checker is locked until {until.strftime('%Y-%m-%d %H:%M:%S')} due to multiple failed attempts.", 'error')
            return render_template('grammar_login.html', locked=locked, unlock_time=until)

        password = request.form.get('password', '')
        ok = password == GRAMMAR_PASSWORD
        ip = _client_ip()

        try:
            log_auth_attempt(FEATURE_NAME, ip, ok, None)
        except Exception as e:
            app.logger.error(f"Failed to log auth attempt: {e}")

        if ok:
            session['grammar_authenticated'] = True
            flash('Logged in to Grammar Checker.', 'success')
            # Notify owner of successful login
            try:
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                subject = 'Grammar Checker login success'
                body = f'Successful login to Grammar Checker.\nTime: {now}\nIP: {ip}'
                _send_email(OWNER_EMAIL, subject, body)
            except Exception as e:
                app.logger.error(f'Email notify (success) failed: {e}')
            return redirect(url_for('grammar'))
        else:
            # After a failure, check if we reached 3 consecutive failures
            try:
                fails = get_consecutive_fail_count(FEATURE_NAME)
                # Notify owner of wrong password attempt
                try:
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    subject = 'Grammar Checker wrong password attempt'
                    body = f'Wrong password entered for Grammar Checker.\nTime: {now}\nIP: {ip}\nConsecutive fails: {fails}'
                    _send_email(OWNER_EMAIL, subject, body)
                except Exception as e:
                    app.logger.error(f'Email notify (failure) failed: {e}')

                if fails >= 3:
                    # Record a lock event
                    try:
                        log_auth_attempt(FEATURE_NAME, ip, None, 'LOCK')
                    except Exception as e:
                        app.logger.error(f"Failed to record lock: {e}")
                    locked = True
                    # Notify owner of lockout
                    try:
                        subject = 'Grammar Checker locked out for 24 hours'
                        body = f'Grammar Checker has been locked due to 3 consecutive failed attempts.\nIP (last attempt): {ip}'
                        _send_email(OWNER_EMAIL, subject, body)
                    except Exception as e:
                        app.logger.error(f'Email notify (lock) failed: {e}')
                    # Recompute until based on now + 24h on the server side when checking lock
                
            except Exception as e:
                app.logger.error(f"Failed to compute consecutive fails: {e}")

            flash('Incorrect password.', 'error')
            return render_template('grammar_login.html', locked=locked, unlock_time=until)

    # GET
    return render_template('grammar_login.html', locked=locked, unlock_time=until)


@app.route('/grammar/request-reset', methods=['GET', 'POST'])
def grammar_request_reset():
    # Ensure schema
    try:
        from .blog_db import init_schema, is_locked, create_reset_token
    except ImportError:
        from blog_db import init_schema, is_locked, create_reset_token
    try:
        init_schema()
    except Exception as e:
        app.logger.error(f"DB schema init failed on request-reset: {e}")

    locked, until = (False, None)
    try:
        locked, until = is_locked(FEATURE_NAME)
    except Exception as e:
        app.logger.error(f"Lock check failed on request-reset: {e}")

    # Always allow generating a reset token; especially relevant when locked
    try:
        token = create_reset_token(FEATURE_NAME)
        reset_url = url_for('grammar_reset', token=token, _external=True)
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = 'Grammar Checker password reset/unlock link'
        body = (
            f'A reset/unlock was requested for Grammar Checker.\n\n'
            f'Time: {now}\n'
            f'Link: {reset_url}\n\n'
            f'This link will unlock access immediately.'
        )
        if _send_email(OWNER_EMAIL, subject, body):
            flash('A reset link has been sent to the owner email.', 'success')
        else:
            flash('Failed to send reset link email. Please check email configuration.', 'error')
    except Exception as e:
        app.logger.error(f"Failed to create/send reset token: {e}")
        flash('Could not generate a reset link. Try again later.', 'error')

    return redirect(url_for('grammar_login'))


@app.route('/grammar/reset/<token>')
def grammar_reset(token: str):
    try:
        from .blog_db import get_reset_by_token, mark_reset_used, record_unlock
    except ImportError:
        from blog_db import get_reset_by_token, mark_reset_used, record_unlock

    try:
        data = get_reset_by_token(token)
        if not data:
            flash('Invalid or unknown reset token.', 'error')
            return redirect(url_for('grammar_login'))
        if data['used']:
            flash('This reset token has already been used.', 'error')
            return redirect(url_for('grammar_login'))
        # Check expiry
        expires_at = data['expires_at']
        if isinstance(expires_at, str):
            # In case DB driver returns string; best-effort parse
            try:
                expires_at = datetime.datetime.fromisoformat(expires_at)
            except Exception:
                pass
        if expires_at and datetime.datetime.now() > expires_at:
            flash('This reset token has expired.', 'error')
            return redirect(url_for('grammar_login'))

        # Record unlock and mark used
        record_unlock(data['feature'])
        mark_reset_used(token)
        flash('Grammar Checker lock has been cleared. You can try logging in again.', 'success')
    except Exception as e:
        app.logger.error(f"Reset token handling failed: {e}")
        flash('Failed to process reset token.', 'error')

    return redirect(url_for('grammar_login'))


@app.route('/grammar/logout')
def grammar_logout():
    session.pop('grammar_authenticated', None)
    flash('Logged out from Grammar Checker.', 'success')
    return redirect(url_for('grammar_login'))


# New explicit route for grammar checker (protected)
@app.route('/grammar')
def grammar():
    """Protected route path for the grammar checker UI"""
    if not session.get('grammar_authenticated'):
        return redirect(url_for('grammar_login'))
    # Also refuse if feature is currently locked
    try:
        from .blog_db import is_locked
    except ImportError:
        from blog_db import is_locked
    try:
        locked, until = is_locked(FEATURE_NAME)
        if locked:
            flash(f"Grammar Checker is locked until {until.strftime('%Y-%m-%d %H:%M:%S')}", 'error')
            return redirect(url_for('grammar_login'))
    except Exception:
        pass
    return render_template('index.html')

# New explicit route for blog homepage path alias
@app.route('/blog-home')
def blog_home():
    """Alias path that routes to the blog homepage"""
    return redirect(url_for('blog'))

@app.route('/upload', methods=['POST'])
def upload_file():
    # Require authentication for grammar upload endpoint
    if not session.get('grammar_authenticated'):
        return jsonify({'error': 'Not authenticated'}), 403
    # Check lock status
    try:
        from .blog_db import is_locked
    except ImportError:
        from blog_db import is_locked
    try:
        locked, until = is_locked(FEATURE_NAME)
        if locked:
            return jsonify({'error': f'Locked until {until.strftime("%Y-%m-%d %H:%M:%S")}' }), 423
    except Exception:
        pass
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
