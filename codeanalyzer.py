import ast
import sys
import os
import time

BRACKETS = {")": "(", "}": "{", "]": "["}
CHECK_FOR_COLON = ("if", "elif", "else", "while", "for", "def", "class", "try", "except", "finally")

# CHECK LINE FOR ERRORS
def check_line(line, number, errors, stack, in_string):
    started_inside_brackets = len(stack) > 0

    for col, ch in enumerate(line, start=1):
        if in_string:                            # Validate whether or not the current char is inside a string
            if ch == in_string:
                in_string = None
        elif ch in "\"'":                        # Check for quotation marks and check if a string is starting
            in_string = ch
            string_start = col
        elif ch == "#":                          # Check for comments
            break
        elif ch in "([{":                        # Check for opening brackets
            stack.append((ch, number, col))
        elif ch in BRACKETS:                     # Check if a bracket has a matching bracket
            if not stack or stack[-1][0] != BRACKETS[ch]:
                errors.append((number, col, f"No Matching Brackets: '{ch}'"))
            else:
                stack.pop()

    # Check for unterminated string literals
    if in_string:
        errors.append((number, string_start, "Unterminated String Literal"))

    # Check for missing colon
    if not started_inside_brackets and not stack:
        code = line.split("#")[0].rstrip()
        words = code.split()
        if words and words[0] in CHECK_FOR_COLON and not code.endswith(":"):
            errors.append((number, len(code) + 1, "A Colon is Expected"))

#
def syntax_analyzer(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()

    in_string = None
    errors = []
    stack = []
    ast_parsed = None

    # Check for every line of the source code
    for number, line in enumerate(source.split("\n"), start=1):
        check_line(line, number, errors, stack, in_string)

    # Check for unclosed brackets
    for ch, number, col in stack:
        errors.append((number, col, f"'{ch}' Was Never Closed"))

    # Backup syntax analyzer (the check_line method may fail to catch some error, so ast.parse is used as a backup)
    if not errors:
        try:
            ast.parse(source, filename=path)
        except SyntaxError as e:
            errors.append((e.lineno or 0, e.offset or 0, f"Python Parser: {e.msg}"))

        if len(errors) > 0:
            ast_parsed = True

    # Print error message
    for number, col, message in sorted(errors):
        print(f"{path}:{number}:{col}: {message}\n")
    if not ast_parsed and len(errors) == 1:
        print("YOUR SOURCE CODE HAS: 1 ERROR")
    elif not ast_parsed and len(errors) != 1:
        print(f"YOUR SOURCE CODE HAS: {len(errors)} ERRORS")
    elif ast_parsed == True:
        print("""This error was checked with ast.parse meaning it can only check for one line at a time,
        try to save the file again to check for further error""")

def main():
    path = sys.argv[1]

    last_saved = None

    print(f"Currently monitoring source code for {path}, you may press Ctrl+C to stop.")

    # Checks every one second for new saved
    while True:
        try:
            current_save = os.path.getmtime(path)
        except FileNotFoundError:
            time.sleep(1)
            continue
        if current_save != last_saved:
            last_saved = current_save
            print("=" * 100)
            syntax_analyzer(path)
        time.sleep(1)

try:
    main()
except KeyboardInterrupt:
    print("Monitoring Stopped")