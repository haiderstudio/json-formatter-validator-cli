#!/bin/sh
# Run the formatter on the bundled examples.
# Run from the repo root: sh examples/run-example.sh
# The check run exits 1 because three example files are bad on purpose —
# that is the expected result here.
set -e
cd "$(dirname "$0")/.."
echo "--- format compact.json ---"
python3 src/json_formatter_validator.py examples/compact.json
echo "--- check all example files ---"
python3 src/json_formatter_validator.py --check examples/valid.json examples/compact.json examples/invalid-missing-comma.json examples/invalid-trailing-comma.json examples/invalid-single-quotes.json || true
echo "--- stdin, sorted keys ---"
echo '{"b":1,"a":2}' | python3 src/json_formatter_validator.py --sort-keys
