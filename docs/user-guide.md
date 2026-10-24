# User guide

`codeanalyzer.py` checks one Python source file without executing it. Use
one-shot mode for a report or watch mode while you edit the file.

## Requirements

The project targets Python 3.8 or later. It uses only the Python standard
library.

## Get the project

Clone the repository and enter its directory:

```text
git clone https://github.com/CedYahoo/staticcodeanalyzer.git
cd staticcodeanalyzer
```

On Windows, use `py` instead of `python3` when that is the command for your
Python installation.

## Analyze once

Run one analysis with the `--once` option:

```text
python3 codeanalyzer.py examples/clean_sample.py --once
```

The command prints `no issues found` for a clean file. The issues sample
contains deliberate findings:

```text
python3 codeanalyzer.py examples/issues_sample.py --once
```

## Monitor a file

Monitoring is the default mode:

```text
python3 codeanalyzer.py path/to/file.py
```

The watcher checks the file immediately. It polls modification time, size, and
file identity after each interval. It analyzes the file again when that
signature changes. If the file is missing, the watcher waits for it to appear.
Press `Ctrl+C` to stop.

## Get JSON output

Add `--format json` to return the source path, issue counts, and diagnostics:

```text
python3 codeanalyzer.py examples/issues_sample.py --once --format json
```

In monitoring mode, each analysis produces one JSON object on a separate line.
Status messages go to standard error, so standard output remains machine-readable.

## Command-line options

| Argument | Default | Use |
| --- | --- | --- |
| `path` | Required | Path to one Python source file. |
| `--once` | Watch mode | Analyze once and exit. |
| `--format {text,json}` | `text` | Choose text or JSON diagnostics. |
| `--interval SECONDS` | `1.0` | Set the positive polling interval in watch mode. |
| `--max-line-length N` | `120` | Set the line-length warning limit. Use `0` to disable it. |
| `--help` | None | Show command help and exit. |

The command rejects a nonpositive interval and a negative line-length limit.

## Diagnostic codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `LEX001` | Error | A string literal is not closed. |
| `LEX002` | Error | A closing bracket has no matching opener. |
| `LEX003` | Error | An opening bracket is not closed. |
| `SYN001` | Error | A selected block statement is missing a colon. |
| `PY001` | Error | Python's parser rejected the source. |
| `PY002` | Warning | The syntax tree is too deeply nested for all checks to run. |
| `IO001` | Error | The analyzer could not read the source file. |
| `F401` | Warning | An imported name appears unused. |
| `E722` | Warning | An `except` clause catches every exception. |
| `B006` | Warning | A function uses a mutable default value. |
| `S307` | Warning | The source calls `eval()`. |
| `S102` | Warning | The source calls `exec()`. |
| `R001` | Warning | Division or modulo uses the literal value zero. |
| `E501` | Warning | A line exceeds the configured limit. |

The analyzer applies AST-based rules only when Python parses the source. File
read errors use line and column `0`. Some name checks use simple syntax-tree
matching, so dynamic name lookup can cause an unused-import warning.

## Exit statuses

| Status | Meaning in one-shot mode |
| --- | --- |
| `0` | The analyzer found no diagnostics. |
| `1` | The analyzer reported at least one error or warning. |
| `2` | The file could not be read or the command line was invalid. |
