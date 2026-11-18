import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from relaydesk.engine import DATA


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = Path(tmp.name) / "review.sqlite3"

    def cli(self, *args, status=0):
        p = subprocess.run([sys.executable, "-m", "relaydesk", "--db", str(self.db), *args],
                           capture_output=True, text=True, cwd=DATA.parent)
        self.assertEqual(p.returncode, status, p.stderr or p.stdout)
        return p.stderr if status else json.loads(p.stdout)

    def test_preview_does_not_persist_and_exact_replay_does_not_retriage(self):
        q = ("northstar", "2025-07-01", "What is the return window?")
        result = self.cli("triage", *q)
        self.assertFalse(self.db.exists())
        submitted = self.cli("submit", "lesson-1", *q)
        self.assertEqual(submitted["result"], result)
        replay = self.cli("--data-dir", str(self.db.parent / "missing"), "submit", "lesson-1", *q)
        self.assertEqual(replay, submitted)
        for different in (("harbor", *q[1:]), (q[0], "2025-06-30", q[2]), (*q[:2], q[2] + " ")):
            self.assertIn("different input", self.cli("submit", "lesson-1", *different, status=2))
        self.assertEqual(self.cli("pending"), [submitted])
        rejected = self.cli("review", "lesson-1", "reject", "--note", "Manual lookup needed.")
        self.assertEqual(rejected["state"], "rejected")
        self.assertEqual(self.cli("submit", "lesson-1", *q), rejected)
        self.assertEqual(self.cli("pending"), [])
        self.assertIn("only pending", self.cli("review", "lesson-1", "accept", status=2))

    def test_handoff_bypasses_draft_queue_and_accept_is_local_only(self):
        manual = self.cli("submit", "stop", "harbor", "2025-01-05", "How do I report damage?")
        self.assertEqual(manual["state"], "handoff")
        self.assertEqual(self.cli("show", "stop"), manual)
        self.assertIn("only pending", self.cli("review", "stop", "accept", status=2))
        self.cli("submit", "ok", "harbor", "2025-03-01", "How do I report damage?")
        self.assertEqual(self.cli("review", "ok", "accept")["state"], "accepted")
        self.assertEqual(self.cli("pending"), [])

    def test_bad_input_fails_without_inserting_work(self):
        self.assertIn("date", self.cli("submit", "bad", "northstar", "not-a-day", "question", status=2))
        self.assertEqual(self.cli("pending"), [])
