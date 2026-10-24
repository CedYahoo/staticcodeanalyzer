import json
import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import codeanalyzer

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codeanalyzer.py"


class CommandLineTests(unittest.TestCase):
    def run_cli(self, path, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path), *arguments],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_once_mode_returns_zero_for_clean_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.py"
            path.write_text("value = 3\nprint(value)\n", encoding="utf-8")
            result = self.run_cli(path, "--once")
        self.assertEqual(0, result.returncode)
        self.assertIn("no issues found", result.stdout)

    def test_json_mode_reports_diagnostics_and_nonzero_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.py"
            path.write_text("if ready\n    pass\n", encoding="utf-8")
            result = self.run_cli(path, "--once", "--format", "json")
        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertEqual(str(path), payload["path"])
        self.assertEqual(1, payload["summary"]["errors"])
        self.assertEqual("SYN001", payload["diagnostics"][0]["code"])
        diagnostic = payload["diagnostics"][0]
        self.assertTrue({"path", "line", "column", "code", "severity", "message"}.issubset(diagnostic))
        self.assertEqual(1, diagnostic["line"])
        self.assertGreater(diagnostic["column"], 0)
        self.assertEqual("error", diagnostic["severity"])

    def test_missing_file_returns_exit_code_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.py"
            result = self.run_cli(path, "--once")
        self.assertEqual(2, result.returncode)
        self.assertIn("IO001", result.stdout)

    def test_invalid_interval_is_rejected_before_watch_starts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.py"
            path.write_text("value = 1\n", encoding="utf-8")
            result = self.run_cli(path, "--interval", "0")
        self.assertEqual(2, result.returncode)
        self.assertIn("must be greater than zero", result.stderr)

    def test_importing_cli_does_not_start_monitoring(self):
        result = subprocess.run(
            [sys.executable, "-c", "import codeanalyzer; print('imported')"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual("imported\n", result.stdout)
        self.assertEqual("", result.stderr)

    def test_watch_reanalyzes_and_emits_json_when_the_file_signature_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "watched.py"
            path.write_text("value = 1\n", encoding="utf-8")
            output = io.StringIO()
            signatures = [(1, 10, 1), (2, 10, 1)]
            sleep_results = [None, KeyboardInterrupt()]
            with contextlib.redirect_stderr(io.StringIO()), patch.object(
                codeanalyzer, "_file_signature", side_effect=signatures
            ), patch.object(codeanalyzer, "_emit", wraps=codeanalyzer._emit) as emit, patch.object(
                codeanalyzer.time, "sleep", side_effect=sleep_results
            ):
                with contextlib.redirect_stdout(output), self.assertRaises(KeyboardInterrupt):
                    codeanalyzer.watch_file(path, interval=0.1, output_format="json")

        self.assertEqual(2, emit.call_count)
        payloads = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(2, len(payloads))
        self.assertTrue(all(payload["path"] == str(path) for payload in payloads))


if __name__ == "__main__":
    unittest.main()
