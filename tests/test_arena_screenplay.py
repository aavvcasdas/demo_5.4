import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "skills/arena-screenplay/scripts/arena_screenplay_check.py"
REVIEW = ROOT / "skills/arena-screenplay/scripts/arena_screenplay_review.py"


class ArenaScreenplayTests(unittest.TestCase):
    def run_check(self, text):
        with tempfile.TemporaryDirectory(prefix="arena_screenplay_") as tmp:
            path = Path(tmp) / "剧本.md"
            path.write_text(text, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECK), str(path), "--json"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            return result, json.loads(result.stdout)

    def test_mechanical_pass_does_not_claim_editorial_approval(self):
        result, report = self.run_check(
            "# EP001\n\n## EP001-SC001 内·厨房·夜\n\n小周把门反锁，手机停在未接来电上。\n\n小周：你再敲，我就报警。\n"
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["mechanical_status"], "PASS")
        self.assertEqual(report["editorial_status"], "REQUIRED")
        self.assertEqual(report["release_status"], "NOT_READY")
        self.assertTrue(report["body_text_sha256"])

    def test_empty_scene_is_blocked(self):
        result, report = self.run_check("# EP001\n\n## EP001-SC001 内·客厅·日\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["mechanical_status"], "BLOCKED")
        self.assertTrue(any(item["code"] == "EMPTY_SCENE" for item in report["findings"]))

    def test_audit_metadata_is_not_silent(self):
        _, report = self.run_check(
            "# EP001\n\n## EP001-SC001 外·街口·日\n\n审核报告说本场 PASS。\n角色：走。\n"
        )
        self.assertTrue(any(item["code"] == "AUDIT_META_IN_BODY" for item in report["findings"]))
        self.assertEqual(report["editorial_status"], "REQUIRED")

    def test_review_scaffold_is_provisional(self):
        with tempfile.TemporaryDirectory(prefix="arena_review_") as tmp:
            root = Path(tmp)
            body = root / "剧本.md"
            out = root / "审核.md"
            body.write_text(
                "# EP001\n\n## EP001-SC001 内·房间·夜\n\n灯灭了。\n\n甲：别出声。\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(REVIEW), str(body), "--output", str(out)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0)
            text = out.read_text(encoding="utf-8")
            self.assertIn("editorial_status: `REQUIRED`", text)
            self.assertIn("release_status: `NOT_READY`", text)
            self.assertIn("body_text_sha256:", text)


if __name__ == "__main__":
    unittest.main()
