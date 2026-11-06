#!/usr/bin/env python3
"""Tests for json_formatter_validator. Standard library unittest only."""

import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from json_formatter_validator import (  # noqa: E402
    describe_error,
    format_text,
    run,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXAMPLES = ROOT / "examples"


def run_cli(argv, stdin_text=None):
    """Run the CLI in-process and capture stdout/stderr. Returns (code, out, err)."""
    out = io.StringIO()
    err = io.StringIO()
    code = run(argv, stdin_text=stdin_text, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


class TestFormatText(unittest.TestCase):
    def test_pretty_default_indent_two(self):
        _value, formatted = format_text('{"b":1,"a":2}')
        self.assertEqual(formatted, '{\n  "b": 1,\n  "a": 2\n}')

    def test_sort_keys(self):
        _value, formatted = format_text('{"b":1,"a":2}', sort_keys=True)
        self.assertEqual(formatted, '{\n  "a": 2,\n  "b": 1\n}')

    def test_minify(self):
        _value, formatted = format_text('{\n  "a": 1\n}', minify=True)
        self.assertEqual(formatted, '{"a":1}')

    def test_indent_four(self):
        _value, formatted = format_text('{"a":{"b":1}}', indent=4)
        self.assertEqual(formatted, '{\n    "a": {\n        "b": 1\n    }\n}')

    def test_indent_zero(self):
        _value, formatted = format_text('{"a":1}', indent=0)
        self.assertEqual(formatted, '{\n"a": 1\n}')

    def test_bad_json_raises_with_line_col(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            format_text('{\n  "a": 1\n  "b": 2\n}')
        self.assertEqual((caught.exception.lineno, caught.exception.colno), (3, 3))

    def test_empty_text_raises_at_1_1(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            format_text("")
        self.assertEqual((caught.exception.lineno, caught.exception.colno), (1, 1))

    def test_trailing_data_raises(self):
        with self.assertRaises(json.JSONDecodeError) as caught:
            format_text('{"a":1} extra')
        self.assertEqual(caught.exception.msg, "Extra data")

    def test_non_ascii_is_escaped(self):
        _value, formatted = format_text('{"name":"café"}')
        self.assertIn("\\u00e9", formatted)
        self.assertNotIn("café", formatted)


class TestDescribeError(unittest.TestCase):
    def test_report_line_and_pointer(self):
        text = '{\n  "a": 1\n  "b": 2\n}'
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            lines = describe_error("bad.json", text, error)
        self.assertEqual(lines[0], "INVALID bad.json:3:3: Expecting ',' delimiter")
        self.assertEqual(lines[1], '    "b": 2')
        self.assertEqual(lines[2], "    ^")

    def test_empty_text_has_no_pointer(self):
        try:
            json.loads("")
        except json.JSONDecodeError as error:
            lines = describe_error("<stdin>", "", error)
        self.assertEqual(lines, ["INVALID <stdin>:1:1: Expecting value"])


class TestCliFormat(unittest.TestCase):
    def test_format_file_to_stdout(self):
        code, out, _err = run_cli([str(EXAMPLES / "compact.json")])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), json.loads((EXAMPLES / "compact.json").read_text()))

    def test_format_matches_pretty_example(self):
        code, out, _err = run_cli([str(EXAMPLES / "compact.json")])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), (EXAMPLES / "valid.json").read_text().strip())

    def test_stdin_with_sort_keys(self):
        code, out, _err = run_cli(["--sort-keys"], stdin_text='{"b":1,"a":2}')
        self.assertEqual(code, 0)
        self.assertEqual(out, '{\n  "a": 2,\n  "b": 1\n}\n')

    def test_minify_flag(self):
        code, out, _err = run_cli(["--minify", str(EXAMPLES / "valid.json")])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), (EXAMPLES / "compact.json").read_text().strip())

    def test_two_files_without_check_is_usage_error(self):
        code, _out, err = run_cli(
            [str(EXAMPLES / "valid.json"), str(EXAMPLES / "compact.json")]
        )
        self.assertEqual(code, 2)
        self.assertIn("more than one file", err)

    def test_missing_file_is_exit_2(self):
        code, _out, err = run_cli([str(EXAMPLES / "nope.json")])
        self.assertEqual(code, 2)
        self.assertIn("file not found", err)

    def test_bad_indent_is_exit_2(self):
        code, _out, err = run_cli(["--indent", "99", str(EXAMPLES / "valid.json")])
        self.assertEqual(code, 2)
        self.assertIn("--indent must be 0-8", err)

    def test_runs_from_any_folder(self):
        # The CLI takes a path, so it must work from any working directory.
        import os

        old = os.getcwd()
        try:
            os.chdir("/tmp")
            code, out, _err = run_cli([str(EXAMPLES / "compact.json")])
        finally:
            os.chdir(old)
        self.assertEqual(code, 0)
        self.assertIn('"name": "example-site"', out)


class TestCliCheck(unittest.TestCase):
    def test_check_valid_and_invalid_mixed(self):
        code, out, _err = run_cli(
            [
                "--check",
                str(EXAMPLES / "valid.json"),
                str(EXAMPLES / "compact.json"),
                str(EXAMPLES / "invalid-missing-comma.json"),
                str(EXAMPLES / "invalid-trailing-comma.json"),
                str(EXAMPLES / "invalid-single-quotes.json"),
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("VALID   %s" % (EXAMPLES / "valid.json"), out)
        self.assertIn("VALID   %s" % (EXAMPLES / "compact.json"), out)
        self.assertIn("INVALID %s:4:3: Expecting ',' delimiter" % (EXAMPLES / "invalid-missing-comma.json"), out)
        self.assertIn(
            "INVALID %s:4:1: Expecting property name enclosed in double quotes"
            % (EXAMPLES / "invalid-trailing-comma.json"),
            out,
        )
        self.assertIn(
            "INVALID %s:2:3: Expecting property name enclosed in double quotes"
            % (EXAMPLES / "invalid-single-quotes.json"),
            out,
        )

    def test_check_all_valid_exits_zero(self):
        code, out, _err = run_cli(
            ["--check", str(EXAMPLES / "valid.json"), str(EXAMPLES / "compact.json")]
        )
        self.assertEqual(code, 0)
        self.assertEqual(out.count("VALID"), 2)

    def test_check_bad_stdin(self):
        code, out, _err = run_cli(["--check"], stdin_text='{"a":1} extra')
        self.assertEqual(code, 1)
        self.assertIn("INVALID <stdin>:1:9: Extra data", out)

    def test_check_empty_stdin(self):
        code, out, _err = run_cli(["--check"], stdin_text="")
        self.assertEqual(code, 1)
        self.assertIn("INVALID <stdin>:1:1: Expecting value", out)

    def test_missing_comma_pointer_line(self):
        code, out, _err = run_cli(
            ["--check", str(EXAMPLES / "invalid-missing-comma.json")]
        )
        self.assertEqual(code, 1)
        self.assertIn('    "private": false', out)
        self.assertIn("    ^", out)


class TestCliWriteModes(unittest.TestCase):
    def test_in_place_rewrites_and_reports(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.json"
            target.write_text((EXAMPLES / "compact.json").read_text())
            code, out, _err = run_cli(["--in-place", str(target)])
            self.assertEqual(code, 0)
            self.assertIn("formatted %s" % target, out)
            self.assertEqual(target.read_text().strip(), (EXAMPLES / "valid.json").read_text().strip())

    def test_in_place_leaves_bad_file_alone(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bad.json"
            original = (EXAMPLES / "invalid-missing-comma.json").read_text()
            target.write_text(original)
            code, out, _err = run_cli(["--in-place", str(target)])
            self.assertEqual(code, 1)
            self.assertEqual(target.read_text(), original)

    def test_output_writes_named_file_input_unchanged(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "out.json"
            code, out, _err = run_cli(
                ["--output", str(dest), str(EXAMPLES / "compact.json")]
            )
            self.assertEqual(code, 0)
            self.assertIn("formatted %s -> %s" % (EXAMPLES / "compact.json", dest), out)
            self.assertEqual(dest.read_text().strip(), (EXAMPLES / "valid.json").read_text().strip())

    def test_format_does_not_change_input_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a.json"
            original = (EXAMPLES / "compact.json").read_text()
            target.write_text(original)
            code, _out, _err = run_cli([str(target)])
            self.assertEqual(code, 0)
            self.assertEqual(target.read_text(), original)

    def test_output_with_two_files_is_usage_error(self):
        code, _out, err = run_cli(
            ["--output", "out.json", str(EXAMPLES / "valid.json"), str(EXAMPLES / "compact.json")]
        )
        self.assertEqual(code, 2)
        self.assertIn("--output needs exactly one input file", err)

    def test_in_place_with_stdin_is_usage_error(self):
        code, _out, err = run_cli(["--in-place"], stdin_text='{"a":1}')
        self.assertEqual(code, 2)
        self.assertIn("--in-place needs a file", err)

    def test_output_with_check_is_usage_error(self):
        code, _out, err = run_cli(
            ["--output", "out.json", "--check", str(EXAMPLES / "valid.json")]
        )
        self.assertEqual(code, 2)
        self.assertIn("--output cannot be used with --check", err)


class TestExamplesAndDocs(unittest.TestCase):
    def test_sample_output_matches_real_run(self):
        """examples/sample-output.txt must be the real output of the check run."""
        result = subprocess.run(
            [
                sys.executable,
                "src/json_formatter_validator.py",
                "--check",
                "examples/valid.json",
                "examples/compact.json",
                "examples/invalid-missing-comma.json",
                "examples/invalid-trailing-comma.json",
                "examples/invalid-single-quotes.json",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stdout, (EXAMPLES / "sample-output.txt").read_text()
        )

    def test_readme_shows_real_outputs(self):
        """The README's quoted outputs must appear in the real runs."""
        readme = (ROOT / "README.md").read_text()
        sample = (EXAMPLES / "sample-output.txt").read_text()
        for line in sample.strip().splitlines():
            self.assertIn(line, readme)

    def test_run_example_script_works(self):
        result = subprocess.run(
            ["sh", str(EXAMPLES / "run-example.sh")],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("VALID", result.stdout)
        self.assertIn("INVALID", result.stdout)


class TestStdlibOnly(unittest.TestCase):
    def test_no_third_party_imports(self):
        allowed = set(sys.stdlib_module_names) | {"json_formatter_validator"}
        for path in [ROOT / "src" / "json_formatter_validator.py", Path(__file__)]:
            tree = __import__("ast").parse(path.read_text())
            for node in __import__("ast").walk(tree):
                if isinstance(node, __import__("ast").Import):
                    for name in node.names:
                        self.assertIn(name.name.split(".")[0], allowed, path)
                elif isinstance(node, __import__("ast").ImportFrom):
                    if node.module:
                        self.assertIn(node.module.split(".")[0], allowed, path)


if __name__ == "__main__":
    unittest.main()
