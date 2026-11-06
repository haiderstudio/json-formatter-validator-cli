#!/usr/bin/env python3
"""Format and validate JSON, with line:col errors, fail CI on bad JSON.

Run: python3 src/json_formatter_validator.py data.json
     python3 src/json_formatter_validator.py --check data.json other.json
     cat data.json | python3 src/json_formatter_validator.py
     python3 src/json_formatter_validator.py --in-place data.json
     python3 src/json_formatter_validator.py --output pretty.json data.json

The tool reads one JSON file (or standard input), pretty-formats it, and
validates it. A bad file is reported with the exact line and column of the
error, plus the offending line with a caret under the bad spot — so you can
find the mistake without opening an editor and hunting for it.

It never rewrites a file unless you ask: --in-place rewrites the input
file, --output writes the formatted text to the file you name. With no
output flag, the formatted text goes to standard output and the input file
is left alone. --check only validates and prints VALID / INVALID per file.

Exit codes: 0 when every file is valid, 1 when any file has bad JSON,
2 for a usage or input problem (missing file, bad flag, --output with
more than one input file).

Python standard library only.
"""

import argparse
import json
import sys
from pathlib import Path

VERSION = "1.0.0"


def build_parser():
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="json_formatter_validator",
        description=(
            "Format and validate JSON. Prints formatted JSON to standard "
            "output, or with --check prints VALID / INVALID per file. "
            "Exits 1 on bad JSON, 2 on a usage problem."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="JSON file to format or check. No file reads standard input.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only validate: print VALID or INVALID per file, do not print JSON.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Rewrite each input file with the formatted JSON.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the formatted JSON to this file instead of standard output.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        metavar="N",
        help="Spaces per indent level (0-8, default 2). Ignored with --minify.",
    )
    parser.add_argument(
        "--sort-keys",
        action="store_true",
        help="Sort object keys alphabetically in the output.",
    )
    parser.add_argument(
        "--minify",
        action="store_true",
        help="Write compact JSON with no extra spaces or newlines.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s " + VERSION,
    )
    return parser


def format_text(text, indent=2, sort_keys=False, minify=False):
    """Parse JSON text and return (value, formatted_text).

    Raises json.JSONDecodeError on bad JSON, exactly as the stdlib
    reports it (with lineno and colno).
    """
    value = json.loads(text)
    if minify:
        formatted = json.dumps(
            value, sort_keys=sort_keys, separators=(",", ":"), ensure_ascii=True
        )
    else:
        formatted = json.dumps(
            value, indent=indent, sort_keys=sort_keys, ensure_ascii=True
        )
    return value, formatted


def describe_error(source, text, error):
    """Build the error report lines for a JSONDecodeError.

    Returns a list of lines: the one-line report with line:col, then the
    offending source line and a caret under the bad column, when the
    source line exists.
    """
    lines = [
        "INVALID %s:%d:%d: %s" % (source, error.lineno, error.colno, error.msg)
    ]
    source_lines = text.splitlines()
    if 1 <= error.lineno <= len(source_lines):
        lines.append("  " + source_lines[error.lineno - 1])
        lines.append("  " + " " * (error.colno - 1) + "^")
    return lines


def read_input(path):
    """Read a file as UTF-8 text. Raises OSError / UnicodeDecodeError."""
    return Path(path).read_text(encoding="utf-8")


def process_one(source, text, indent, sort_keys, minify, check, out_lines):
    """Format or check one input. Returns True when the JSON is valid.

    Appends report lines to out_lines. In format mode the formatted JSON
    itself is returned as the second value; in check mode it is None.
    """
    try:
        _value, formatted = format_text(text, indent, sort_keys, minify)
    except json.JSONDecodeError as error:
        out_lines.extend(describe_error(source, text, error))
        return False, None
    if check:
        out_lines.append("VALID   %s" % source)
        return True, None
    return True, formatted


def run(argv=None, stdin_text=None, stdout=None, stderr=None):
    """Run the CLI. Returns the exit code. Testable without subprocess."""
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.indent < 0 or args.indent > 8:
        print("error: --indent must be 0-8", file=stderr)
        return 2
    if args.output and args.check:
        print("error: --output cannot be used with --check", file=stderr)
        return 2
    if args.output and args.in_place:
        print("error: --output cannot be used with --in-place", file=stderr)
        return 2
    if args.in_place and args.check:
        print("error: --in-place cannot be used with --check", file=stderr)
        return 2
    if args.in_place and not args.files:
        print("error: --in-place needs a file, it cannot rewrite stdin", file=stderr)
        return 2
    if args.output and len(args.files) != 1:
        print("error: --output needs exactly one input file", file=stderr)
        return 2
    if not args.check and len(args.files) > 1 and not args.in_place:
        print(
            "error: formatting more than one file needs --check or --in-place",
            file=stderr,
        )
        return 2

    inputs = []  # list of (source_name, text)
    if not args.files:
        if stdin_text is None:
            stdin_text = sys.stdin.read()
        inputs.append(("<stdin>", stdin_text))
    else:
        for path in args.files:
            try:
                inputs.append((path, read_input(path)))
            except FileNotFoundError:
                print("error: file not found: %s" % path, file=stderr)
                return 2
            except OSError as exc:
                print("error: cannot read %s: %s" % (path, exc), file=stderr)
                return 2
            except UnicodeDecodeError:
                print("error: %s is not valid UTF-8 text" % path, file=stderr)
                return 2

    all_valid = True
    for source, text in inputs:
        out_lines = []
        valid, formatted = process_one(
            source, text, args.indent, args.sort_keys, args.minify, args.check, out_lines
        )
        if not valid:
            all_valid = False
            for line in out_lines:
                print(line, file=stdout)
            continue
        if args.check:
            print(out_lines[0], file=stdout)
        elif args.in_place:
            Path(source).write_text(formatted + "\n", encoding="utf-8")
            print("formatted %s" % source, file=stdout)
        elif args.output:
            Path(args.output).write_text(formatted + "\n", encoding="utf-8")
            print("formatted %s -> %s" % (source, args.output), file=stdout)
        else:
            print(formatted, file=stdout)

    return 0 if all_valid else 1


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
