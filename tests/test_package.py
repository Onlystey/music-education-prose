from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


class PackageTests(unittest.TestCase):
    def run_tool(self, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PYTHON, *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_manifest_and_package_checker_pass(self) -> None:
        result = self.run_tool("tools/check_package.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_evals_cover_positive_and_negative_cases(self) -> None:
        document = json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
        cases = document["cases"]
        self.assertEqual({case["kind"] for case in cases}, {"positive", "negative"})
        self.assertGreaterEqual(sum(case["kind"] == "positive" for case in cases), 3)
        self.assertGreaterEqual(sum(case["kind"] == "negative" for case in cases), 3)
        for case in cases:
            self.assertTrue(case["pass_checks"])
            self.assertTrue(case["fail_signals"])

    def test_install_is_scoped_verifiable_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            install_args = ("tools/install.py", "--project", str(project))
            installed = self.run_tool(*install_args)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)

            target = project / ".agents/skills/music-education-prose"
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertTrue((target / "agents/openai.yaml").is_file())
            self.assertTrue((target / "references/music-language.md").is_file())
            self.assertFalse((target / "evals").exists())
            self.assertFalse((target / "tests").exists())

            verified = self.run_tool("tools/install.py", "--project", str(project), "--verify")
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            repeated = self.run_tool(*install_args)
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)

    def test_installer_refuses_to_overwrite_unmanaged_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "project"
            target = project / ".agents/skills/music-education-prose"
            target.mkdir(parents=True)
            user_file = target / "README.md"
            user_file.write_text("keep this local file\n", encoding="utf-8")

            result = self.run_tool("tools/install.py", "--project", str(project))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(user_file.read_text(encoding="utf-8"), "keep this local file\n")

    def test_checker_detects_a_changed_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy = Path(temporary) / "music-education-prose"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("__pycache__", ".git"))
            reference = copy / "references/music-language.md"
            reference.write_text(reference.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            result = self.run_tool("tools/check_package.py", cwd=copy)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
