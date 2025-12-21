import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import datetime

from flask import Flask, request, jsonify, abort

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

import MySQLdb

# --------------------------------------------------
# Load .env
# --------------------------------------------------
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# --------------------------------------------------
# App Config
# --------------------------------------------------
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")   # IMPORTANT
APP_PORT = int(os.getenv("APP_PORT", "5000"))
APP_API_KEY = os.getenv("APP_API_KEY")        # simple auth layer

# --------------------------------------------------
# MySQL LOCAL Config (NOT exposed)
# --------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "local_app_db")

# --------------------------------------------------
# Flask App
# --------------------------------------------------
app = Flask(__name__)

# --------------------------------------------------
# Simple API Key Protection
# --------------------------------------------------
def require_api_key():
    key = request.headers.get("X-API-KEY")
    if not APP_API_KEY or key != APP_API_KEY:
        abort(401, description="Unauthorized")

# --------------------------------------------------
# Database Helpers
# --------------------------------------------------
def _ensure_database_exists():
    conn = MySQLdb.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        passwd=DB_PASSWORD,
        charset="utf8mb4",
        use_unicode=True,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            f"""
            CREATE DATABASE IF NOT EXISTS `{DB_NAME}`
            DEFAULT CHARACTER SET utf8mb4
            COLLATE utf8mb4_unicode_ci;
            """
        )
        conn.commit()
    finally:
        conn.close()


def open_connection():
    _ensure_database_exists()
    return MySQLdb.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        passwd=DB_PASSWORD,
        db=DB_NAME,
        charset="utf8mb4",
        use_unicode=True,
    )


def close(conn):
    try:
        conn.close()
    except Exception:
        pass

# --------------------------------------------------
# Schema
# --------------------------------------------------
def init_schema():
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                entry_key VARCHAR(64) UNIQUE,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(128) NOT NULL,
                created_at DATETIME NOT NULL,
                content LONGTEXT NOT NULL
            ) CHARACTER SET utf8mb4;
            """
        )
        conn.commit()
    finally:
        close(conn)

# --------------------------------------------------
# API Routes (SAFE TO EXPOSE)
# --------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

@app.route("/entries", methods=["GET"])
def get_entries():
    require_api_key()
    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT entry_key, title, author, created_at, content
            FROM entries
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        return jsonify([
            {
                "id": r[0],
                "title": r[1],
                "author": r[2],
                "date": r[3].strftime("%Y-%m-%d %H:%M:%S"),
                "content": r[4],
            }
            for r in rows
        ])
    finally:
        close(conn)

@app.route("/entries", methods=["POST"])
def insert_entry():
    require_api_key()
    data = request.json or {}

    title = data.get("title")
    content = data.get("content")
    author = data.get("author")

    if not title or not content or not author:
        abort(400, "Missing required fields")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    entry_key = f"{timestamp}_{title.replace(' ', '_')}"

    conn = open_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO entries (entry_key, title, author, created_at, content)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (entry_key, title, author, datetime.datetime.now(), content)
        )
        conn.commit()
        return {"id": entry_key}, 201
    finally:
        close(conn)

# --------------------------------------------------
# Main
# --------------------------------------------------
if __name__ == "__main__":
    init_schema()
    app.run(
        host=APP_HOST,   # 0.0.0.0 = external access
        port=APP_PORT,
        debug=False      # NEVER True when exposed
    )
