"""
Deprecated: SSH tunneling has been removed from the project.

This file previously created an SSH tunnel to connect to MySQL. All SSH-related
code and configuration have been deleted. Connect directly to your database
using the `Blog.blog_db` module and the following environment variables in Blog/.env:

  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

This module is intentionally left as a stub to avoid import errors.
"""

raise RuntimeError(
    "db_setup.py has been deprecated. Use direct DB connection via Blog.blog_db and env vars (DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME)."
)