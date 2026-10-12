"""Static checks for Python source without executing the analyzed program."""

from __future__ import annotations

import ast
import tokenize
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


BRACKET_PAIRS = {")": "(", "]": "[", "}": "{"}
OPEN_BRACKETS = {"(": ")", "[": "]", "{": "}"}
BLOCK_KEYWORDS = {"if", "elif", "else", "while", "for", "def", "class", "try", "except", "finally"}


@dataclass(frozen=True)
class Diagnostic:
    """A location-specific analyzer finding."""

    path: str
    line: int
    column: int
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _diagnostic(path: str, line: int, column: int, code: str, severity: str, message: str) -> Diagnostic:
    return Diagnostic(path, max(0, line), max(0, column), code, severity, message)


def _has_odd_trailing_backslashes(value: str) -> bool:
    count = 0
    for character in reversed(value):
        if character != "\\":
            break
        count += 1
    return count % 2 == 1


def _scan_source(source: str, path: str) -> list[Diagnostic]:
    """Run the project's small character-level checks.

    Python's parser remains authoritative. These checks add clearer messages for
    common delimiter, quote, and block-header mistakes when parsing fails.
    """

    diagnostics = []
    bracket_stack = []
    quote = None
    triple_quoted = False
    quote_start = None
    escaped = False
    lines = source.splitlines(keepends=True)

    for line_number, raw_line in enumerate(lines, start=1):
        content = raw_line.rstrip("\r\n")
        visible = list(content)
        started_inside_brackets = bool(bracket_stack)
        header_colon_found = False
        index = 0

        while index < len(content):
            character = content[index]

            if quote is not None:
                visible[index] = " "
                if escaped:
                    escaped = False
                    index += 1
                    continue
                if character == "\\":
                    escaped = True
                    index += 1
                    continue
                if triple_quoted and content.startswith(quote * 3, index):
                    for offset in range(index, index + 3):
                        visible[offset] = " "
                    quote = None
                    triple_quoted = False
                    quote_start = None
                    index += 3
                    continue
                if not triple_quoted and character == quote:
                    quote = None
                    quote_start = None
                index += 1
                continue

            if character == "#":
                for offset in range(index, len(visible)):
                    visible[offset] = " "
                break

            if character in ("'", '"'):
                triple_quoted = content.startswith(character * 3, index)
                quote = character
                quote_start = (line_number, index + 1)
                width = 3 if triple_quoted else 1
                for offset in range(index, index + width):
                    visible[offset] = " "
                index += width
                continue

            if character == ":" and not bracket_stack:
                header_colon_found = True
            if character in OPEN_BRACKETS:
                bracket_stack.append((character, line_number, index + 1))
            elif character in BRACKET_PAIRS:
                if not bracket_stack or bracket_stack[-1][0] != BRACKET_PAIRS[character]:
                    diagnostics.append(_diagnostic(
                        path, line_number, index + 1, "LEX002", "error",
                        "Closing delimiter {!r} has no matching opening delimiter.".format(character),
                    ))
                else:
                    bracket_stack.pop()
            index += 1

        # A triple-quoted string may span lines. A single-quoted string may
        # continue only when its line ends with an escaped newline.
        if quote is not None:
            if triple_quoted:
                escaped = False
            elif escaped:
                escaped = False
            else:
                diagnostics.append(_diagnostic(
                    path, quote_start[0], quote_start[1], "LEX001", "error",
                    "Unterminated string literal.",
                ))
                quote = None
                quote_start = None

        code = "".join(visible)
        stripped = code.strip()
        if (
            stripped
            and not started_inside_brackets
            and not bracket_stack
            and quote is None
            and not _has_odd_trailing_backslashes(code.rstrip())
        ):
            first_word = stripped.split(None, 1)[0]
            if first_word in BLOCK_KEYWORDS and not header_colon_found:
                diagnostics.append(_diagnostic(
                    path, line_number, len(code.rstrip()) + 1, "SYN001", "error",
                    "Expected ':' after the {!r} statement header.".format(first_word),
                ))

    if quote is not None:
        diagnostics.append(_diagnostic(
            path, quote_start[0], quote_start[1], "LEX001", "error",
            "Unterminated string literal.",
        ))

    for opening, line_number, column in bracket_stack:
        diagnostics.append(_diagnostic(
            path, line_number, column, "LEX003", "error",
            "Opening delimiter {!r} is never closed (expected {!r}).".format(
                opening, OPEN_BRACKETS[opening]
            ),
        ))

    return diagnostics


def _literal_export_names(tree: ast.AST) -> set:
    """Return string names listed in a literal __all__ assignment."""

    exported = set()
    for node in ast.walk(tree):
        value = None
        targets = []
        if isinstance(node, ast.Assign):
            value = node.value
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            targets = [node.target]
        elif isinstance(node, ast.AugAssign):
            value = node.value
            targets = [node.target]

        if value is None or not any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in targets
        ):
            continue
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            exported.update(
                element.value for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
    return exported


def _is_mutable_default(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"list", "dict", "set"}
        and not node.args
        and not node.keywords
    )


def _is_literal_zero(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, (int, float, complex)) and node.value == 0
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.UAdd, ast.USub))
        and isinstance(node.operand, ast.Constant)
    ):
        value = node.operand.value
        return isinstance(value, (int, float, complex)) and value == 0
    return False


class _RuleVisitor(ast.NodeVisitor):
    def __init__(self, tree: ast.AST, path: str, source: str) -> None:
        self.path = path
        self.is_package_initializer = Path(path).name == "__init__.py"
        self.source_lines = source.splitlines()
        self.used_names = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        self.exported_names = _literal_export_names(tree)
        self.diagnostics = []

    def _column(self, node: ast.AST) -> int:
        line_number = getattr(node, "lineno", 0) or 0
        byte_column = getattr(node, "col_offset", 0) or 0
        if 1 <= line_number <= len(self.source_lines):
            encoded_prefix = self.source_lines[line_number - 1].encode("utf-8")[:byte_column]
            return len(encoded_prefix.decode("utf-8", errors="ignore")) + 1
        return byte_column + 1

    def _add(self, node: ast.AST, code: str, message: str, severity: str = "warning") -> None:
        self.diagnostics.append(_diagnostic(
            self.path,
            getattr(node, "lineno", 0) or 0,
            self._column(node),
            code,
            severity,
            message,
        ))

    def visit_Import(self, node: ast.Import) -> None:
        if self.is_package_initializer:
            return
        for alias in node.names:
            bound_name = alias.asname or alias.name.partition(".")[0]
            if bound_name != "_" and bound_name not in self.used_names and bound_name not in self.exported_names:
                self._add(alias, "F401", "Imported name {!r} is never used.".format(bound_name))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.is_package_initializer:
            return
        if node.module == "__future__":
            return
        for alias in node.names:
            if alias.name == "*":
                continue
            bound_name = alias.asname or alias.name
            if bound_name != "_" and bound_name not in self.used_names and bound_name not in self.exported_names:
                self._add(alias, "F401", "Imported name {!r} is never used.".format(bound_name))

    def _check_defaults(self, arguments: ast.arguments) -> None:
        defaults = list(arguments.defaults) + [value for value in arguments.kw_defaults if value is not None]
        for default in defaults:
            if _is_mutable_default(default):
                self._add(
                    default, "B006",
                    "Mutable default value is shared between calls; use None and create it inside the function.",
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_defaults(node.args)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_defaults(node.args)
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._check_defaults(node.args)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add(node, "E722", "Bare 'except' catches every exception; name the exception type.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id == "eval":
                self._add(node.func, "S307", "Use of eval() executes a dynamically constructed expression.")
            elif node.func.id == "exec":
                self._add(node.func, "S102", "Use of exec() executes dynamically constructed code.")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and _is_literal_zero(node.right):
            self._add(node.right, "R001", "Division or modulo by the literal value zero will fail at runtime.")
        self.generic_visit(node)


def _line_length_diagnostics(source: str, path: str, maximum: Optional[int]) -> list[Diagnostic]:
    if maximum is None or maximum == 0:
        return []
    diagnostics = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        length = len(line)
        if length > maximum:
            diagnostics.append(_diagnostic(
                path, line_number, maximum + 1, "E501", "warning",
                "Line is {} characters long (limit: {}).".format(length, maximum),
            ))
    return diagnostics


def analyze_source(source: str, path: str = "<string>", max_line_length: Optional[int] = 120) -> list[Diagnostic]:
    """Analyze Python source and return sorted diagnostics without executing it."""

    if max_line_length is not None and max_line_length < 0:
        raise ValueError("max_line_length must be 0, a positive integer, or None")

    diagnostics = []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        diagnostics.extend(_scan_source(source, path))
        error_line = error.lineno or 0
        if not any(item.line == error_line for item in diagnostics):
            diagnostics.append(_diagnostic(
                path,
                error_line,
                error.offset or 0,
                "PY001",
                "error",
                "Python syntax error: {}".format(error.msg),
            ))
    else:
        visitor = _RuleVisitor(tree, path, source)
        try:
            visitor.visit(tree)
            diagnostics.extend(visitor.diagnostics)
        except RecursionError:
            diagnostics.append(_diagnostic(
                path, 0, 0, "PY002", "warning",
                "Some static checks were skipped because the syntax tree is nested too deeply.",
            ))

    diagnostics.extend(_line_length_diagnostics(source, path, max_line_length))
    unique = set(diagnostics)
    return sorted(unique, key=lambda item: (item.line, item.column, item.code, item.message))


def analyze_file(path: str, max_line_length: Optional[int] = 120) -> list[Diagnostic]:
    """Read and analyze a Python file, honoring its declared source encoding."""

    file_path = Path(path)
    try:
        with tokenize.open(str(file_path)) as source_file:
            source = source_file.read()
    except (OSError, UnicodeError, SyntaxError, LookupError) as error:
        return [_diagnostic(
            str(file_path), 0, 0, "IO001", "error",
            "Cannot read source file: {}".format(error),
        )]
    return analyze_source(source, path=str(file_path), max_line_length=max_line_length)
