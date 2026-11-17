import sys
from pathlib import Path

# Ensure CEIS_backend is in sys.path
backend_dir = Path(__file__).resolve().parent / "CEIS_backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app  # noqa: F401
