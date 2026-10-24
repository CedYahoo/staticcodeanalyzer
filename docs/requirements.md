# Project requirements

These requirements define the current behavior of `analyzer.py` and
`codeanalyzer.py`. The verification column names tests in the repository.

## Functional requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| FR-01 | The analyzer shall read one Python source file and honor its declared source encoding. | `test_file_reader_honors_python_encoding_cookie` |
| FR-02 | The analyzer shall inspect source without importing or executing it. | `test_file_analysis_does_not_execute_source` |
| FR-03 | The analyzer shall report parser errors and specific delimiter, string, or selected missing-colon findings when available. | `test_reports_mismatched_and_unclosed_brackets`, `test_reports_unterminated_string_once`, `test_reports_missing_colon_with_source_location` |
| FR-04 | For valid syntax, the analyzer shall report unused imports, bare exception handlers, mutable defaults, direct `eval()` and `exec()` calls, and division by literal zero. | `test_reports_static_quality_and_safety_issues`, `test_reports_exec_calls` |
| FR-05 | The analyzer shall report lines above the configured limit. A limit of `0` shall disable this check. | `test_reports_configurable_line_length` |
| FR-06 | Each diagnostic shall include a path, line, column, code, severity, and message. | `test_json_mode_reports_diagnostics_and_nonzero_status` |
| FR-07 | The CLI shall support one-shot analysis and file monitoring. | `test_once_mode_returns_zero_for_clean_source`, `test_watch_reanalyzes_and_emits_json_when_the_file_signature_changes` |
| FR-08 | The CLI shall support text and JSON output. Monitoring JSON shall contain one object per analysis. | `test_json_mode_reports_diagnostics_and_nonzero_status`, `test_watch_reanalyzes_and_emits_json_when_the_file_signature_changes` |
| FR-09 | One-shot mode shall return `0` with no findings, `1` when it reports diagnostics, and `2` for file-read or argument errors. | `test_once_mode_returns_zero_for_clean_source`, `test_json_mode_reports_diagnostics_and_nonzero_status`, `test_missing_file_returns_exit_code_two`, `test_invalid_interval_is_rejected_before_watch_starts` |
| FR-10 | Importing the CLI module shall not start file monitoring. | `test_importing_cli_does_not_start_monitoring` |

## Non-functional requirements

| ID | Requirement | Verification |
| --- | --- | --- |
| NFR-01 | The analyzer and tests shall use only the Python standard library. | Source and test import review. |
| NFR-02 | Diagnostics shall be returned in stable source-location order. | `test_diagnostics_are_sorted_by_source_location` |
| NFR-03 | The code shall target Python 3.8 or later. | Python 3.8 grammar compatibility check. |

## Scope boundaries

The analyzer covers selected syntax, style, and safety findings. It does not
provide complete type checking, data-flow analysis, or security auditing.
`F401` can miss dynamic name use or references hidden by scope shadowing. The
direct `eval()` and `exec()` checks can warn on local functions with those
names.
