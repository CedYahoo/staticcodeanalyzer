import tempfile
import unittest
from pathlib import Path

from analyzer import analyze_file, analyze_source


class AnalyzeSourceTests(unittest.TestCase):
    def codes(self, source, max_line_length=0):
        return {item.code for item in analyze_source(source, max_line_length=max_line_length)}

    def test_accepts_escaped_quotes_comments_and_brackets_in_strings(self):
        source = 'message = "a \\"quote\\" and # text"  # comment [\nitems = [1, 2]\n'
        self.assertEqual([], analyze_source(source, max_line_length=0))

    def test_accepts_single_quoted_string_continued_with_backslash(self):
        source = 'message = "first\\\nsecond"\n'
        self.assertEqual([], analyze_source(source, max_line_length=0))

    def test_accepts_multiline_strings_and_ignores_their_contents(self):
        source = (
            'text = """opening [ and # are string contents\n'
            'closing ) and ordinary "quotes"\n'
            '"""\n'
            'items = [1, 2]\n'
        )
        self.assertEqual([], analyze_source(source, max_line_length=0))

    def test_reports_mismatched_and_unclosed_brackets(self):
        diagnostics = analyze_source("values = [1, 2)\n", max_line_length=0)
        self.assertIn("LEX002", {item.code for item in diagnostics})
        self.assertIn("LEX003", {item.code for item in diagnostics})
        self.assertFalse(any(item.code == "PY001" for item in diagnostics))

    def test_reports_unterminated_string_once(self):
        diagnostics = analyze_source('message = "unfinished\n', max_line_length=0)
        string_errors = [item for item in diagnostics if item.code == "LEX001"]
        self.assertEqual(1, len(string_errors))
        self.assertEqual(1, string_errors[0].line)
        self.assertFalse(any(item.code == "PY001" for item in diagnostics))

    def test_reports_missing_colon_with_source_location(self):
        diagnostics = analyze_source("if ready\n    pass\n", max_line_length=0)
        self.assertEqual(1, len(diagnostics))
        self.assertEqual("SYN001", diagnostics[0].code)
        self.assertEqual((1, 9), (diagnostics[0].line, diagnostics[0].column))

    def test_valid_one_line_suite_is_not_reported_as_missing_colon(self):
        self.assertEqual([], analyze_source('if ready: print("yes")\n', max_line_length=0))

    def test_one_line_suite_error_is_not_mislabeled_as_missing_colon(self):
        diagnostics = analyze_source("if ready: print(\n", max_line_length=0)
        codes = {item.code for item in diagnostics}
        self.assertNotIn("SYN001", codes)
        self.assertIn("LEX003", codes)

    def test_reports_static_quality_and_safety_issues(self):
        source = (
            "import math\n"
            "import os\n"
            "def calculate(values=[]):\n"
            "    try:\n"
            "        return math.sqrt(values[0] / 0) + eval('1 + 1')\n"
            "    except:\n"
            "        return 0\n"
        )
        codes = self.codes(source)
        self.assertTrue({"F401", "B006", "E722", "S307", "R001"}.issubset(codes))

    def test_reports_exec_calls(self):
        self.assertIn("S102", self.codes("exec('x = 1')\n"))

    def test_deep_syntax_tree_does_not_crash_static_checks(self):
        source = "+".join(["1"] * 500)
        diagnostics = analyze_source(source, max_line_length=0)
        self.assertIn("PY002", {item.code for item in diagnostics})

    def test_literal_all_exports_count_as_uses(self):
        source = 'from math import pi\n__all__ = ["pi"]\n'
        self.assertNotIn("F401", self.codes(source))

    def test_future_imports_are_not_marked_unused(self):
        source = "from __future__ import annotations\nvalue: list[int] = []\n"
        self.assertNotIn("F401", self.codes(source))

    def test_package_initializer_imports_are_treated_as_public_reexports(self):
        diagnostics = analyze_source("from .core import Analyzer\n", path="pkg/__init__.py")
        self.assertNotIn("F401", {item.code for item in diagnostics})

    def test_reports_configurable_line_length(self):
        diagnostics = analyze_source("result = 123\n", max_line_length=8)
        line_warning = next(item for item in diagnostics if item.code == "E501")
        self.assertEqual(9, line_warning.column)
        self.assertIn("E501", self.codes("result = 123\n", max_line_length=5))
        self.assertNotIn("E501", self.codes("result = 123\n", max_line_length=0))

    def test_file_reader_honors_python_encoding_cookie(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "latin.py"
            path.write_bytes(b"# -*- coding: latin-1 -*-\nname = 'caf\xe9'\n")
            self.assertEqual([], analyze_file(str(path), max_line_length=0))

    def test_missing_file_returns_a_diagnostic_instead_of_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.py"
            diagnostics = analyze_file(str(missing))
        self.assertEqual(["IO001"], [item.code for item in diagnostics])


if __name__ == "__main__":
    unittest.main()
