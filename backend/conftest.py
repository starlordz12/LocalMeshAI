"""Make the backend package importable (``config``, ``models``, ``services``) regardless of
where pytest is invoked from, and point project storage at a temp dir during tests."""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Isolate test projects from the real workspace.
os.environ.setdefault("LOCALMESHAI_PROJECTS", tempfile.mkdtemp(prefix="lmai_tests_"))
