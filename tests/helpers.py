"""A window-free StudyGenie for tests.

These tests combine the logic mixins with a plain object, so they run
without opening a window, and point storage at a throwaway SQLite database."""

import shutil
import tempfile
from pathlib import Path

from app.content import ContentMixin
from app.db import DataMixin
from app.progress import ProgressMixin
from app.notebook import NotesMixin
from app.scheduling import SchedulingMixin


class FakeApp(ContentMixin, DataMixin, ProgressMixin, SchedulingMixin, NotesMixin):
    def __init__(self, db_path, legacy_json_path):
        self._last_db_error = None
        self.db_path = db_path
        self.legacy_json_path = Path(legacy_json_path)
        self.init_db()
        self.data = self.load_data()
        self.note_id = None
        self._review_order = {}
        self._review_counter = 0
        self.celebrations = []

    # UI hooks the logic calls; recorded instead of drawn.
    def refresh_status(self):
        pass

    def celebrate(self, title, subtitle):
        self.celebrations.append(title)

    def after(self, _ms, callback):
        callback()


class AppTestCase:
    """Mixin for unittest.TestCase: gives each test a fresh FakeApp in a temp folder."""

    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="studygenie-test-"))
        self.db_path = self.tmp / "data.db"
        self.json_path = self.tmp / "legacy.json"
        self.app = self.make_app()

    def make_app(self):
        return FakeApp(self.db_path, self.json_path)

    def reopen(self):
        """Closes the database and loads it again, like restarting the app."""
        self.app.conn.close()
        self.app = self.make_app()
        return self.app

    def tearDown(self):
        try:
            self.app.conn.close()
        except Exception:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()
