# json-formatter-validator-cli

Format and validate JSON, with line:col errors, fail CI on bad JSON.

[![CI](https://github.com/haiderstudio/json-formatter-validator-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/json-formatter-validator-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`json_formatter_validator` reads a JSON file (or standard input),
pretty-formats it, and validates it. A bad file is reported with the
exact line and column of the error, plus the offending line with a
caret under the bad spot — so you can find the mistake without
opening an editor and hunting for it.

- It formats one file to standard output by default (2-space indent).
  `--indent N` changes the indent, `--sort-keys` sorts object keys,
  `--minify` writes compact JSON with no extra spaces or newlines.
- It reads from standard input when no file is named, so it works in
  a pipe.
- `--check` only validates: it prints `VALID` or `INVALID` per file
  and checks as many files as you name. It exits 1 when any file has
  bad JSON, so it can fail a CI run.
- It never rewrites a file unless you ask: `--in-place` rewrites the
  input file, `--output FILE` writes the formatted text to the file
  you name. A bad file is never rewritten — it is reported and left
  alone.
- It is report-only and runs fully offline: it sends nothing anywhere
  and needs no API key.

## What it does NOT do

- It does not check JSON against a schema. It checks syntax only: can
  a parser read this text, and where exactly does it break.
- It does not fix bad JSON. A missing comma is reported with its line
  and column, not repaired.
- It does not check duplicate keys, and it does not warn about them.
  Two keys with the same name are read the way Python's `json` module
  reads them (the last one wins).
- It does not query, filter, or transform JSON. If you need to pick
  fields out of a document, that is a different tool's job.
- It does not accept comments, trailing commas, or single quotes.
  Those are not JSON, and they are reported as errors.

## Who it is for

Anyone who keeps JSON files around and wants a quick, scriptable
check that they are well-formed: a developer adding a CI step that
fails the build on a broken config, someone hand-editing a settings
file, or anyone piping API output through a formatter to read it. If
the file is valid, you get clean formatted JSON; if it is not, the
report says exactly which line and column broke.

## How this differs from similar tools

JSON formatters already exist, and most of them are web pages or
editors: JSONLint and jsonformatter.org format in a browser, and the
top GitHub hit for the exact name, mariazevedo88/json-formatter-validator
(12 stars), is a Java tool. The big command-line name in this space
is jq, but jq is a query and transform language — formatting is a
side effect of it, not its job, and it needs a separate install.
Python already ships `python -m json.tool`, which pretty-prints and
exits nonzero on bad JSON, but it reports only the error message: no
line and column pointer, no `--check` mode for several files at once,
and no `--in-place` or `--output` for writing formatted files.
Schema validators such as the ajv CLI or jsonvalidator-cli check JSON
against a schema, which is a different job from checking syntax.

This tool does a narrower job: a Python standard-library-only CLI
that formats one file or checks many, reports every error with a
line, a column, and a caret, and exits 1 on bad JSON for CI — no
install beyond Python, no browser, no schema, no query language.

## Install

Python standard library only — no packages to download. Clone the
repo and run it in place:

```sh
git clone https://github.com/haiderstudio/json-formatter-validator-cli.git
cd json-formatter-validator-cli
```

Python 3.10 or newer.

## Usage

Format a file:

```sh
python3 src/json_formatter_validator.py examples/compact.json
```

Real output:

```text
{
  "name": "example-site",
  "pages": [
    {
      "draft": false,
      "path": "/",
      "title": "Home"
    },
    {
      "draft": false,
      "path": "/about",
      "title": "About"
    }
  ],
  "private": false,
  "settings": {
    "postsPerPage": 10,
    "theme": "light"
  },
  "version": "1.4.0"
}
```

The command exits 0. The input file is left alone.

Check several files at once:

```sh
python3 src/json_formatter_validator.py --check examples/valid.json examples/compact.json examples/invalid-missing-comma.json examples/invalid-trailing-comma.json examples/invalid-single-quotes.json
```

Real output:

```text
VALID   examples/valid.json
VALID   examples/compact.json
INVALID examples/invalid-missing-comma.json:4:3: Expecting ',' delimiter
    "private": false
    ^
INVALID examples/invalid-trailing-comma.json:4:1: Expecting property name enclosed in double quotes
  }
  ^
INVALID examples/invalid-single-quotes.json:2:3: Expecting property name enclosed in double quotes
    'name': 'example-site',
    ^
```

The command exits 1, because three files are bad. The same output
is saved in `examples/sample-output.txt`.

Format from a pipe, with sorted keys:

```sh
echo '{"b":1,"a":2}' | python3 src/json_formatter_validator.py --sort-keys
```

Real output:

```text
{
  "a": 2,
  "b": 1
}
```

Minify a file:

```sh
python3 src/json_formatter_validator.py --minify examples/valid.json
```

Real output:

```text
{"name":"example-site","pages":[{"draft":false,"path":"/","title":"Home"},{"draft":false,"path":"/about","title":"About"}],"private":false,"settings":{"postsPerPage":10,"theme":"light"},"version":"1.4.0"}
```

## Examples

### 1. Fail CI on a bad config file

```sh
python3 src/json_formatter_validator.py --check config.json
echo $?
```

```text
1
```

The exit code is 1 when the file has bad JSON. Put the same command
in CI and the build fails until the file is fixed. With a valid file
the same command prints `VALID   config.json` and exits 0.

### 2. A missing comma, found by line and column

`examples/invalid-missing-comma.json` is missing the comma after
`"version": "1.4.0"`:

```sh
python3 src/json_formatter_validator.py --check examples/invalid-missing-comma.json
```

```text
INVALID examples/invalid-missing-comma.json:4:3: Expecting ',' delimiter
    "private": false
    ^
```

Line 4, column 3 — the start of `"private"` — is where the parser
expected the comma. The caret points at it.

### 3. Rewrite a file in place, only when asked

```sh
python3 src/json_formatter_validator.py --in-place examples/compact.json
```

```text
formatted examples/compact.json
```

The file is now pretty-printed. Without `--in-place` (or
`--output`), the same command prints the formatted text and leaves
the file alone. A bad file is never rewritten, even with
`--in-place`.

## How it is tested

```sh
python3 tests/test_json_formatter_validator.py
```

35 tests, standard library `unittest` only — no third-party
packages. They cover: formatting (default indent, `--indent 4`,
indent 0, `--sort-keys`, `--minify`, non-ASCII escaping), error
positions (missing comma at 4:3, trailing data at 1:9, empty input
at 1:1, trailing comma, single quotes), the `--check` mode (valid
and invalid mixed, all valid, stdin, pointer lines), the write modes
(`--in-place` rewrites and reports, bad files are never rewritten,
`--output` writes a named file, plain formatting never changes the
input), the usage errors (missing file, bad indent, `--output` with
two files, `--in-place` with stdin), the bundled examples (the
committed `examples/sample-output.txt` is compared against a fresh
run, and the README's quoted outputs are checked against it), the
example script, and a check that the code and the tests import
standard library only.

The bundled example is a real run, not made-up output:

```sh
sh examples/run-example.sh
```

It formats `examples/compact.json`, checks all five example files,
and formats one line from stdin. The committed
`examples/sample-output.txt` is the output of the check run.

## Contributing

Small, focused improvements are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

Built from scratch for this repo. The JSON parsing and error
positions come from Python's standard `json` module; no code was
copied from any existing formatter or validator.
