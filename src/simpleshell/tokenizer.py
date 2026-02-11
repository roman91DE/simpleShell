"""Tokenize shell input into tokens, properly handling operators and quotes."""

import shlex

# Characters that are part of "words" (filenames, arguments), not operators
_EXTRA_WORDCHARS = ".-_/~${}*?@%+=,:0123456789"

PIPE = "|"
REDIRECT_OUT = ">"
REDIRECT_APPEND = ">>"
REDIRECT_IN = "<"
AND = "&&"
OR = "||"
OPERATORS = {PIPE, REDIRECT_OUT, REDIRECT_APPEND, REDIRECT_IN, AND, OR}


def tokenize(line: str) -> list[str]:
    """Tokenize a shell input line.

    Uses shlex for quote handling and escaping, with custom wordchars
    so that |, >, < are recognized as operator tokens even when adjacent
    to words (e.g., 'echo foo>bar' -> ['echo', 'foo', '>', 'bar']).

    Consecutive '>' '>' are merged into '>>', '&' '&' into '&&', '|' '|' into '||'.
    """
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = False
    lexer.wordchars += _EXTRA_WORDCHARS

    raw_tokens = list(lexer)
    return _merge_operators(raw_tokens)


def _merge_operators(tokens: list[str]) -> list[str]:
    """Merge consecutive '>' into '>>', '&' '&' into '&&', '|' '|' into '||'."""
    merged: list[str] = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i] == tokens[i + 1] and tokens[i] in (">", "&", "|"):
            merged.append(tokens[i] * 2)
            i += 2
        else:
            merged.append(tokens[i])
            i += 1
    return merged
