# Static code analyzer

`codeanalyzer.py` checks one Python source file without executing it. It reports
syntax errors and selected code-quality and safety findings.

## Quick start

Analyze a sample once:

```text
python3 codeanalyzer.py examples/clean_sample.py --once
```

Monitor a file while you edit it:

```text
python3 codeanalyzer.py path/to/file.py
```

The default mode watches the file. Press `Ctrl+C` to stop. On Windows, use `py`
when that is the command for your Python installation.

## Documentation

- [User guide](docs/user-guide.md) covers setup, commands, output, and diagnostic codes.
- [Developer guide](docs/developer-guide.md) covers code structure, tests, and rule changes.
- [Project requirements](docs/requirements.md) defines testable behavior and scope limits.
- [Tutorial](tutorial.md) points to the user guide.

## Tests

Run the standard-library test suite from the repository root:

```text
python3 -m unittest discover -v
```
