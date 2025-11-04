import os
import sys
import importlib
import pytest

"""
Integration test to confirm MySQL connectivity via db_setup.health_check().

How to run locally:
- Create projects/Blog/.env with your real credentials (never commit it).
- Set DB_CONNECT_MODE=direct (inside PythonAnywhere) or DB_CONNECT_MODE=ssh with SSH vars (outside PA).
- Install deps: pip install -r projects/Blog/requirements.txt and pytest.
- Run with RUN_DB_INTEGRATION=1, e.g.:
  - PowerShell:
      set RUN_DB_INTEGRATION=1; pytest -k test_db_connection
  - Bash:
      RUN_DB_INTEGRATION=1 pytest -k test_db_connection

TODO(security/CI): Convert to a mock-based unit test for CI, or keep this as an
optional integration test only. Do not gate CI on live DB connectivity.
"""

# Allow running from repo root by adding Blog directory to sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
BLOG_DIR = os.path.dirname(HERE)
if BLOG_DIR not in sys.path:
    sys.path.insert(0, BLOG_DIR)

# Best-effort: load local env for developer runs
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.path.join(BLOG_DIR, '.env'))
except Exception:
    pass


@pytest.mark.integration
@pytest.mark.skipif(os.getenv('RUN_DB_INTEGRATION', '0').lower() not in ('1', 'true', 'yes'),
                    reason='Set RUN_DB_INTEGRATION=1 to run DB connectivity test')
def test_health_db_connectivity():
    db_setup = importlib.import_module('db_setup')
    ok = db_setup.health_check()
    assert ok is True, (
        'health_check() returned False. Ensure required env vars are set: '
        'PA_DB_HOST/MYSQL_HOST, PA_DB_PORT/MYSQL_PORT, PA_DB_USER/MYSQL_USER, '
        'PA_DB_PASS/MYSQL_PASSWORD, PA_DB_NAME/MYSQL_DATABASE; and if using ssh, '
        'PA_SSH_HOST, PA_SSH_USER, and PA_SSH_PASS or PA_SSH_KEY; set DB_CONNECT_MODE accordingly.'
    )
