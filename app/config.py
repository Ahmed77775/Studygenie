"""Where the app keeps its files.

Data stays beside the launcher (studygenie.py), exactly where it was
before the code was split into this package."""

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent
DB_PATH = DATA_DIR / "studygenie_data.db"
LEGACY_JSON_PATH = DATA_DIR / "studygenie_data.json"
ICON_PATH = DATA_DIR / "studygenie.ico"  # window icon for both versions
