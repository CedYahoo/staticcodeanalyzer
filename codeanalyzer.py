"""Command-line interface and file watcher for the static analyzer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from analyzer import Diagnostic, analyze_file


def format_text(path: str, diagnostics: list[Diagnostic]) -> str:
    if not diagnostics:
        return "{}: no issues found.".format(path)

    lines = []
    for diagnostic in diagnostics:
        if diagnostic.line:
            location = "{}:{}:{}".format(diagnostic.path, diagnostic.line, diagnostic.column)
        else:
            location = diagnostic.path
        lines.append("{}: {} {}: {}".format(
            location,
            diagnostic.severity.upper(),
            diagnostic.code,
            diagnostic.message,
        ))

    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = len(diagnostics) - errors
    lines.append("{} issue(s): {} error(s), {} warning(s).".format(len(diagnostics), errors, warnings))
    return "\n".join(lines)


def format_json(path: str, diagnostics: list[Diagnostic]) -> str:
    errors = sum(item.severity == "error" for item in diagnostics)
    warnings = len(diagnostics) - errors
    result = {
        "path": path,
        "summary": {"issues": len(diagnostics), "errors": errors, "warnings": warnings},
        "diagnostics": [item.to_dict() for item in diagnostics],
    }
    return json.dumps(result, ensure_ascii=False)


def _emit(path: Path, diagnostics: list[Diagnostic], output_format: str) -> None:
    if output_format == "json":
        print(format_json(str(path), diagnostics), flush=True)
    else:
        print(format_text(str(path), diagnostics), flush=True)


def _file_signature(path: Path):
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size, getattr(stat, "st_ino", 0)


def watch_file(
    path: Path,
    interval: float = 1.0,
    output_format: str = "text",
    max_line_length: int = 120,
) -> None:
    """Reanalyze the file whenever it is created, replaced, or modified."""

    print("Monitoring {} every {} second(s). Press Ctrl+C to stop.".format(path, interval), file=sys.stderr)
    previous_signature = None
    waiting_reported = False
    last_stat_error = None

    while True:
        try:
            signature = _file_signature(path)
        except OSError as error:
            message = str(error)
            if message != last_stat_error:
                print("Cannot inspect {}: {}".format(path, message), file=sys.stderr, flush=True)
                last_stat_error = message
            previous_signature = None
            time.sleep(interval)
            continue

        last_stat_error = None
        if signature is None:
            previous_signature = None
            if not waiting_reported:
                print("Waiting for {} to appear...".format(path), file=sys.stderr, flush=True)
                waiting_reported = True
        else:
            waiting_reported = False
            if signature != previous_signature:
                _emit(path, analyze_file(str(path), max_line_length=max_line_length), output_format)
                previous_signature = signature
        time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze Python syntax and common static issues without running the source file."
    )
    parser.add_argument("path", type=Path, help="Python source file to analyze")
    parser.add_argument(
        "--once",
        action="store_true",
        help="analyze once and exit instead of monitoring the file (default mode watches)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="diagnostic output format (JSON mode emits one JSON object per analysis)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="seconds between file checks in monitoring mode (default: 1)",
    )
    parser.add_argument(
        "--max-line-length",
        type=int,
        default=120,
        help="warn when a source line exceeds this length; use 0 to disable (default: 120)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.max_line_length < 0:
        parser.error("--max-line-length cannot be negative")

    if args.once:
        diagnostics = analyze_file(str(args.path), max_line_length=args.max_line_length)
        _emit(args.path, diagnostics, args.format)
        if any(item.code == "IO001" for item in diagnostics):
            return 2
        return 1 if diagnostics else 0

    try:
        watch_file(
            args.path,
            interval=args.interval,
            output_format=args.format,
            max_line_length=args.max_line_length,
        )
    except KeyboardInterrupt:
        print("Monitoring stopped.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
