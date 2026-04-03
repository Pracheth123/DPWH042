"""
tests/conftest.py
-----------------
Force mock_db backend during tests.

The DB toggle in app/db/__init__.py reads SUPABASE_URL at import time.
If the developer's .env has real Supabase credentials, the toggle would
route to supabase_db — which is wrong for unit tests that seed and clear
the in-memory MOCK_DB list.

This conftest.py patches the environment BEFORE any app module is imported
by pytest, ensuring the toggle always picks mock_db in the test process.
"""

import os

# Blank out Supabase env vars so the toggle in app/db/__init__.py
# falls back to mock_db.  This must happen before any app imports.
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""
