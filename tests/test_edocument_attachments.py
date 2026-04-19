"""Tests for eDocument attachment preview extraction."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_content_agent.edocument_attachments import extract_attachment_preview


class EDocumentAttachmentTests(unittest.TestCase):
    def test_extract_attachment_preview_for_csv(self) -> None:
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            path.write_text("col1,col2\nalpha,beta\ngamma,delta\n", encoding="utf-8")

            preview = extract_attachment_preview(path)

            self.assertIn("col1,col2", preview)
            self.assertIn("alpha,beta", preview)


if __name__ == "__main__":
    unittest.main()
