# Developer guide

The analyzer separates source checks from command-line behavior. Keep new
rules deterministic, location-specific, and covered by offline tests.

## Module responsibilities

| Path | Responsibility |
| --- | --- |
| `analyzer.py` | Reads source files, parses Python, applies checks, and creates diagnostics. |
| `codeanalyzer.py` | Parses options, formats results, and monitors file changes. |
| `tests/test_analyzer.py` | Tests parsing, static rules, file reads, and diagnostic locations. |
| `tests/test_cli.py` | Tests options, output formats, exit statuses, and monitoring. |
| `examples/` | Contains source files for clean and warning demonstrations. |

## Analysis flow

`analyze_file()` opens the file with Python's encoding detection. It passes the
text to `analyze_source()`, which first calls `ast.parse()`. When parsing fails,
the character-level scanner looks for clearer delimiter, string, or selected
colon diagnostics. When parsing succeeds, `_RuleVisitor` checks the syntax
tree. The line-length check runs for both valid and invalid source.

The CLI starts monitoring only when `codeanalyzer.py` runs as a script. Importing
the module does not start a watcher. The watcher detects changes through file
modification time, size, and file identity.

## Run the checks

Run the complete offline suite and compile the Python files from the repository
root:

```text
python3 -m unittest discover -v
python3 -m compileall -q analyzer.py codeanalyzer.py tests examples
```

Try both included source examples:

```text
python3 codeanalyzer.py examples/clean_sample.py --once
python3 codeanalyzer.py examples/issues_sample.py --once
```

The second command returns status `1` because the sample contains warnings.

## Add a diagnostic rule

Add a small source fixture and a test before implementing a rule. Put rules that
need syntax structure in `_RuleVisitor`. Put malformed-source checks in
`_scan_source`. Give every diagnostic a stable code, severity, source location,
and short message.

Add source-rule tests to `tests/test_analyzer.py`. Add CLI tests when a public
option, output, or exit status changes. Update the user guide when a diagnostic
code or command option changes. Update the requirements when accepted behavior
changes. Then run the full test and compile commands above.

Never import or run the analyzed source file. Parse it with Python's AST and
inspect only syntax data.

## Known limits

The analyzer does not provide complete type checking, data-flow analysis, or a
full security audit. `F401` uses syntax-tree name references rather than full
scope resolution. Runtime reflection can hide an import use. The direct
`eval()` and `exec()` checks match calls by name, so a local function with the
same name can trigger a warning.
