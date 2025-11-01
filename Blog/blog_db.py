from __future__ import annotations

"""
File-based backend for Blog to remove Paramiko/MySQL dependencies.

This module provides the same public API as the previous DB-backed version but
stores data in JSON files under the Blog directory. This eliminates
any need for paramiko/sshtunnel/MySQL drivers.
"""

from typing import Optional, Dict, Any, List
import os
import json
from datetime import datetime, timedelta
import secrets

# Base directories (relative to this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_ENTRIES_DIR = os.path.join(BASE_DIR, 'blog_entries')
COMMENTS_DIR = os.path.join(BASE_DIR, 'blog_comments')
STATE_DIR = os.path.join(BASE_DIR, '.state')  # internal state (auth attempts, reset tokens)
AUTH_ATTEMPTS_FILE = os.path.join(STATE_DIR, 'auth_attempts.json')
RESET_TOKENS_FILE = os.path.join(STATE_DIR, 'reset_tokens.json')

# --- Helpers ---

def _ensure_dirs() -> None:
    os.makedirs(BLOG_ENTRIES_DIR, exist_ok=True)
    os.makedirs(COMMENTS_DIR, exist_ok=True)
    os.makedirs(STATE_DIR, exist_ok=True)


def _read_json_list(path: str) -> list:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except FileNotFoundError:
        return []
    except Exception:
        return []


def _write_json_list(path: str, items: list) -> None:
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


# --- Schema / init ---

def init_schema() -> None:
    """Ensure required folders/files exist (no real schema)."""
    _ensure_dirs()
    # Initialize state files if missing
    for p in (AUTH_ATTEMPTS_FILE, RESET_TOKENS_FILE):
        if not os.path.exists(p):
            _write_json_list(p, [])


# --- Blog entries CRUD (file-based) ---

def _entry_path(entry_key: str) -> str:
    return os.path.join(BLOG_ENTRIES_DIR, f"{entry_key}.json")


def insert_entry(title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> str:
    _ensure_dirs()
    # Create entry_key like previous code (timestamp + safe title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    entry_key = f"{timestamp}_{safe_title}" if safe_title else timestamp
    data = {
        'id': entry_key,
        'title': title,
        'author': author or 'Anonymous',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'content': content,
        'media': media if isinstance(media, dict) else None,
    }
    with open(_entry_path(entry_key), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return entry_key


def get_entries() -> List[Dict[str, Any]]:
    _ensure_dirs()
    results: List[Dict[str, Any]] = []
    try:
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
                results.append({
                    'id': entry_id,
                    'title': data.get('title') or 'Untitled',
                    'author': data.get('author') or 'Anonymous',
                    'date': data.get('date') or '',
                    'content': data.get('content') or '',
                    'media': data.get('media') if isinstance(data.get('media'), dict) else None,
                })
            except Exception:
                continue
        # Sort by date descending when possible
        def parse_dt(s: str) -> datetime:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d_%H%M%S"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
            return datetime.min
        results.sort(key=lambda e: parse_dt(e.get('date', '')), reverse=True)
    except Exception:
        pass
    return results


def get_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    _ensure_dirs()
    path = _entry_path(entry_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return {
            'id': entry_id,
            'title': data.get('title') or 'Untitled',
            'author': data.get('author') or 'Anonymous',
            'date': data.get('date') or '',
            'content': data.get('content') or '',
            'media': data.get('media') if isinstance(data.get('media'), dict) else None,
        }
    except Exception:
        return None


def update_entry(entry_id: str, title: str, content: str, author: str, media: Optional[Dict[str, Any]] = None) -> bool:
    _ensure_dirs()
    existing = get_entry(entry_id)
    if not existing:
        return False
    updated = {
        'id': entry_id,
        'title': title or existing['title'],
        'author': author or existing['author'],
        'date': existing['date'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'content': content,
        'media': media if isinstance(media, dict) else existing.get('media'),
    }
    try:
        with open(_entry_path(entry_id), 'w', encoding='utf-8') as f:
            json.dump(updated, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def delete_entry(entry_id: str) -> bool:
    _ensure_dirs()
    path = _entry_path(entry_id)
    if not os.path.exists(path):
        return False
    try:
        os.remove(path)
        return True
    except Exception:
        return False


# --- Authentication attempt tracking (file-based) ---

def log_auth_attempt(feature: str, ip: str | None, success: bool | None, note: str | None = None) -> None:
    _ensure_dirs()
    items = _read_json_list(AUTH_ATTEMPTS_FILE)
    items.append({
        'feature': feature,
        'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip': ip,
        'success': (1 if success is True else 0 if success is False else None),
        'note': note,
    })
    _write_json_list(AUTH_ATTEMPTS_FILE, items)


def _iter_attempts(feature: str):
    items = _read_json_list(AUTH_ATTEMPTS_FILE)
    for it in items:
        if isinstance(it, dict) and it.get('feature') == feature:
            yield it


def _parse_ts(val) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(val, fmt)
            except Exception:
                continue
    return None


def get_last_lock_time(feature: str) -> Optional[datetime]:
    last: Optional[datetime] = None
    for it in _iter_attempts(feature):
        if it.get('note') == 'LOCK':
            ts = _parse_ts(it.get('ts'))
            if ts and (last is None or ts > last):
                last = ts
    return last


def get_last_unlock_time(feature: str) -> Optional[datetime]:
    last: Optional[datetime] = None
    for it in _iter_attempts(feature):
        if it.get('note') == 'UNLOCK':
            ts = _parse_ts(it.get('ts'))
            if ts and (last is None or ts > last):
                last = ts
    return last


def record_unlock(feature: str) -> None:
    log_auth_attempt(feature, None, None, 'UNLOCK')


def is_locked(feature: str) -> tuple[bool, Optional[datetime]]:
    last_lock = get_last_lock_time(feature)
    if not last_lock:
        return False, None
    last_unlock = get_last_unlock_time(feature)
    if last_unlock and last_unlock >= last_lock:
        return False, None
    until = last_lock + timedelta(hours=24)
    if datetime.now() < until:
        return True, until
    return False, None


def get_consecutive_fail_count(feature: str) -> int:
    # Read attempts for feature ordered by ts desc
    attempts = list(_iter_attempts(feature))
    # Sort descending by ts
    def key_ts(it):
        dt = _parse_ts(it.get('ts')) or datetime.min
        return dt
    attempts.sort(key=key_ts, reverse=True)
    fails = 0
    for it in attempts:
        if it.get('note') is not None:
            # Skip special events
            continue
        success_val = it.get('success')
        if success_val == 1:
            break
        if success_val == 0:
            fails += 1
    return fails


# --- Reset token helpers (file-based) ---

def create_reset_token(feature: str, lifetime_hours: int = 24) -> str:
    _ensure_dirs()
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(hours=lifetime_hours)
    items = _read_json_list(RESET_TOKENS_FILE)
    items.append({
        'feature': feature,
        'token': token,
        'ts': now.strftime('%Y-%m-%d %H:%M:%S'),
        'expires_at': expires.strftime('%Y-%m-%d %H:%M:%S'),
        'used': 0,
    })
    _write_json_list(RESET_TOKENS_FILE, items)
    return token


def get_reset_by_token(token: str) -> Optional[dict]:
    items = _read_json_list(RESET_TOKENS_FILE)
    for it in items:
        if isinstance(it, dict) and it.get('token') == token:
            # Return a copy with parsed types similar to DB row mapping
            return {
                'id': None,
                'feature': it.get('feature'),
                'token': it.get('token'),
                'ts': it.get('ts'),
                'expires_at': it.get('expires_at'),
                'used': bool(it.get('used')),
            }
    return None


def mark_reset_used(token: str) -> None:
    items = _read_json_list(RESET_TOKENS_FILE)
    changed = False
    for it in items:
        if isinstance(it, dict) and it.get('token') == token:
            it['used'] = 1
            changed = True
            break
    if changed:
        _write_json_list(RESET_TOKENS_FILE, items)
