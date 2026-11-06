# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the JSON file or standard input you name, and it never changes a file unless you ask with `--in-place` or `--output`. It writes nothing except the report on standard output (and usage errors on standard error).

If you find a case where the tool changes a file without `--in-place` or `--output`, or reports a line and column that do not match the real error position, please open an issue describing the exact commands and input. Do not include any real secret in the report.
