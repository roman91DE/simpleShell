"""Variable expansion and glob expansion."""

import glob as globmod
import os
import re

from simpleshell.tokenizer import OPERATORS


def expand_variables(line: str) -> str:
    """Expand $VAR and ${VAR} in the raw input line.

    Respects quoting: variables in single quotes are NOT expanded.
    Variables in double quotes and unquoted contexts ARE expanded.
    Undefined variables expand to empty string.
    """
    result: list[str] = []
    i = 0
    quote: str | None = None  # None, "'", or '"'

    while i < len(line):
        ch = line[i]

        # Handle backslash escape
        if ch == "\\" and i + 1 < len(line):
            result.append(ch)
            result.append(line[i + 1])
            i += 2
            continue

        # Track quote state
        if ch in ("'", '"'):
            if quote is None:
                quote = ch
            elif quote == ch:
                quote = None
            result.append(ch)
            i += 1
            continue

        # Expand $ only outside single quotes
        if ch == "$" and quote != "'":
            expanded, consumed = _expand_one_var(line, i)
            result.append(expanded)
            i += consumed
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _expand_one_var(line: str, pos: int) -> tuple[str, int]:
    """Expand a single variable starting at line[pos] == '$'.

    Returns (expanded_value, characters_consumed).
    Handles $VAR and ${VAR} forms.
    """
    if pos + 1 >= len(line):
        return ("$", 1)

    if line[pos + 1] == "{":
        # ${VAR} form
        end = line.find("}", pos + 2)
        if end == -1:
            return ("${", 2)  # unterminated, treat literally
        name = line[pos + 2 : end]
        value = os.environ.get(name, "")
        return (value, end - pos + 1)

    # $VAR form: consume [a-zA-Z_][a-zA-Z0-9_]*
    match = re.match(r"[a-zA-Z_][a-zA-Z0-9_]*", line[pos + 1 :])
    if not match:
        return ("$", 1)

    name = match.group(0)
    value = os.environ.get(name, "")
    return (value, 1 + len(name))


def expand_globs(tokens: list[str]) -> list[str]:
    """Expand glob patterns (* and ?) in tokens.

    Tokens that match no files are left unchanged.
    Operator tokens are never glob-expanded.
    """
    expanded: list[str] = []
    for token in tokens:
        if token in OPERATORS:
            expanded.append(token)
        elif "*" in token or "?" in token:
            matches = globmod.glob(token)
            if matches:
                expanded.extend(sorted(matches))
            else:
                expanded.append(token)
        else:
            expanded.append(token)
    return expanded


def expand_tilde(tokens: list[str]) -> list[str]:
    """Expand ~ at the start of tokens to the user's home directory."""
    return [os.path.expanduser(t) if t.startswith("~") else t for t in tokens]
