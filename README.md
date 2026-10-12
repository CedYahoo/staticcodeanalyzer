# Static Code Analyzer

A small Python tool that monitors or checks `.py` files without executing them.
It combines targeted source checks with Python's parser and reports findings
with a file, line, and column.

## Requirements

- Python 3.8 or later
- No third-party packages are needed to run the analyzer or its test suite

## Run it

Monitoring is the default and checks the file once immediately, then again when
its modification time, size, or file identity changes:

```text
python codeanalyzer.py examples/clean_sample.py
```

Analyze a file once and exit:

```text
python codeanalyzer.py examples/issues_sample.py --once
```

Get JSON output for scripts and integrations:

```text
python codeanalyzer.py examples/issues_sample.py --once --format json
```

The line-length warning defaults to 120 characters. Use
`--max-line-length 100` to change it or `--max-line-length 0` to disable it.
Use `--interval 0.5` to check for saved changes twice per second.

## Checks

The analyzer reports Python syntax and common source issues:

- mismatched or unclosed brackets, unterminated strings, and missing colons on
  selected block-statement headers;
- Python parser syntax errors;
- unused imports (`F401`), bare `except` clauses (`E722`), mutable function
  defaults (`B006`), direct `eval()` or `exec()` calls (`S307`, `S102`), and
  division or modulo by a literal zero (`R001`);
- lines longer than the configured limit (`E501`).

AST-based checks run only when Python can parse the file. Findings are
diagnostics, not automatic edits. The analyzer never executes the analyzed
source; in particular, it reports calls to `eval()` and `exec()` but never
invokes them.

Some checks are deliberately conservative. For example, the unused-import
check recognizes ordinary name references and literal `__all__` lists. It skips
imports in `__init__.py` because they commonly re-export public names. Runtime
reflection such as `globals()` can still make another import appear unused,
and same-named references in other scopes can hide an unused import. The direct
`eval()` and `exec()` checks are name-based and may warn if a program defines a
local function with the same name. This tool does not provide complete type
checking, data-flow analysis, or security auditing.

## Test

Run the offline test suite with the Python standard library:

```text
python -m unittest discover -v
```
