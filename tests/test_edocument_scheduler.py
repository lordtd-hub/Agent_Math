"""Tests for eDocument scheduler helpers."""

from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from math_content_agent.edocument_scheduler import _prune_old_digest_logs


class EDocumentSchedulerTests(unittest.TestCase):
    def test_prune_old_digest_logs_keeps_active_window(self) -> None:
        with TemporaryDirectory() as temp_dir:
            logs_dir = Path(temp_dir)
            keep_paths = [
                logs_dir / "2026-04-20_edocument_digest.json",
                logs_dir / "2026-04-19_edocument_digest.json",
            ]
            remove_path = logs_dir / "2026-04-18_edocument_digest.json"

            for path in [*keep_paths, remove_path]:
                path.write_text("{}", encoding="utf-8")

            removed = _prune_old_digest_logs(logs_dir, date(2026, 4, 20), 1)

            self.assertEqual(removed, 1)
            self.assertTrue(keep_paths[0].exists())
            self.assertTrue(keep_paths[1].exists())
            self.assertFalse(remove_path.exists())


if __name__ == "__main__":
    unittest.main()
