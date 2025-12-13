r"""
One-off migration script: import all existing .txt blog entries from blog_entries/ into the database (entries table).
- Preserves entry_key as the filename without extension, so existing comment JSON files keyed by entry_id continue to work.
- Skips any entry_key that already exists in the DB.

Run:
  python projects\Grammar_checker\migrate_files_to_db.py
"""
import os
import datetime
from typing import Optional, Dict, Any

# Allow running both as module or script
try:
    from .blog_db import init_schema, open_connection, _close
except ImportError:
    from blog_db import init_schema, open_connection, _close

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_ENTRIES_DIR = os.path.join(BASE_DIR, 'blog_entries')


def parse_entry_file(filepath: str) -> Optional[Dict[str, Any]]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        title = lines[0].replace('Title: ', '') if lines and lines[0].startswith('Title: ') else 'Untitled'
        author = lines[1].replace('Author: ', '') if len(lines) > 1 and lines[1].startswith('Author: ') else 'Anonymous'
        date_str = lines[2].replace('Date: ', '') if len(lines) > 2 and lines[2].startswith('Date: ') else ''

        # Try to parse datetime
        try:
            created_at = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S') if date_str else datetime.datetime.now()
        except Exception:
            created_at = datetime.datetime.now()

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
            line_index += 7

        content_start_index = line_index + 1
        entry_body = '\n'.join(lines[content_start_index:]) if len(lines) > content_start_index else ''

        return {
            'title': title,
            'author': author,
            'created_at': created_at,
            'content': entry_body,
            'media': media,
        }
    except Exception as e:
        print(f"Failed to parse {filepath}: {e}")
        return None


def ensure_entry(conn, entry_key: str, data: Dict[str, Any]) -> bool:
    """Insert if not exists; returns True if inserted or already exists."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM entries WHERE entry_key=%s", (entry_key,))
    if cur.fetchone():
        return True
    cur.execute(
        """
        INSERT INTO entries
        (entry_key, title, author, created_at, content,
         media_id, media_type, media_url, media_thumbnail, media_width, media_height, media_attribution)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            entry_key,
            data['title'],
            data['author'],
            data['created_at'],
            data['content'],
            (data.get('media') or {}).get('id'),
            (data.get('media') or {}).get('type'),
            (data.get('media') or {}).get('url'),
            (data.get('media') or {}).get('thumbnail'),
            (data.get('media') or {}).get('width'),
            (data.get('media') or {}).get('height'),
            (data.get('media') or {}).get('attribution'),
        ),
    )
    conn.commit()
    return True


def main():
    if not os.path.isdir(BLOG_ENTRIES_DIR):
        print('No blog_entries directory found. Nothing to migrate.')
        return

    init_schema()
    conn = open_connection()
    try:
        total = 0
        migrated = 0
        for filename in sorted(os.listdir(BLOG_ENTRIES_DIR)):
            if not filename.endswith('.txt'):
                continue
            total += 1
            entry_key = os.path.splitext(filename)[0]
            filepath = os.path.join(BLOG_ENTRIES_DIR, filename)
            data = parse_entry_file(filepath)
            if not data:
                continue
            if ensure_entry(conn, entry_key, data):
                migrated += 1
                print(f"Upserted: {entry_key}")
        print(f"Done. Processed: {total}. Upserted/exists: {migrated}.")
    finally:
        _close(conn)


if __name__ == '__main__':
    main()
