# Quick start

The Static Code Analyzer checks Python source files without executing them. It
reports syntax errors and selected code-quality or safety issues in the
terminal.

## Monitor a file while editing

From the repository folder, run:

```text
python codeanalyzer.py examples/clean_sample.py
```

Monitoring is the default. The analyzer checks immediately, then checks again
when the file changes. Press `Ctrl+C` to stop.

## Analyze once

```text
python codeanalyzer.py examples/issues_sample.py --once
```

The command exits with `0` when no issues are found, `1` when it reports
diagnostics, and `2` when it cannot read the file or the command is invalid.

## Get machine-readable results

```text
python codeanalyzer.py examples/issues_sample.py --once --format json
```

JSON mode returns one object containing the source path, issue counts, and
diagnostics. In monitoring mode, each analysis is printed as a separate JSON
line.

## Adjust the line-length check

The default line-length limit is 120 characters. Change it or turn it off with:

```text
python codeanalyzer.py examples/clean_sample.py --once --max-line-length 100
python codeanalyzer.py examples/clean_sample.py --once --max-line-length 0
```

## Run the tests

```text
python -m unittest discover -v
```

The analyzer parses source text but never imports or runs the file being
checked. Checks based on names are intentionally limited: dynamic uses through
`globals()`, plugin loading, or other runtime reflection can make an import look
unused even when a program uses it dynamically.
