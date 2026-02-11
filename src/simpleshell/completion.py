"""Readline tab completion for files, directories, and commands."""

import os
import readline
from functools import lru_cache

from simpleshell.builtins import BUILTIN_REGISTRY

_matches: list[str] = []


def setup_completion() -> None:
    """Configure readline for tab completion."""
    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n;|><")
    readline.parse_and_bind("tab: complete")


def invalidate_path_cache() -> None:
    """Clear the cached PATH commands (call after PATH changes)."""
    _get_path_commands.cache_clear()


def completer(text: str, state: int) -> str | None:
    """Readline completer function.

    On state 0, compute all matches. On subsequent states, return the next.
    """
    global _matches

    if state == 0:
        line = readline.get_line_buffer()
        begidx = readline.get_begidx()

        before_cursor = line[:begidx].lstrip()

        if not before_cursor or before_cursor.endswith("|"):
            _matches = _complete_command(text)
        else:
            _matches = _complete_path(text)

    if state < len(_matches):
        return _matches[state]
    return None


def _complete_command(text: str) -> list[str]:
    """Complete a command name from builtins and PATH executables."""
    matches: list[str] = []

    for name in BUILTIN_REGISTRY:
        if name.startswith(text):
            matches.append(name)

    for cmd in _get_path_commands():
        if cmd.startswith(text):
            matches.append(cmd)

    matches.extend(_complete_path(text))

    return sorted(set(matches))


def _complete_path(text: str) -> list[str]:
    """Complete a file or directory path."""
    if text:
        dirname = os.path.dirname(text)
        basename = os.path.basename(text)
        search_dir = dirname or "."
    else:
        search_dir = "."
        basename = ""
        dirname = ""

    matches: list[str] = []
    try:
        for entry in os.listdir(search_dir):
            if entry.startswith(basename):
                full = os.path.join(dirname, entry) if dirname else entry
                if os.path.isdir(os.path.join(search_dir, entry)):
                    full += "/"
                matches.append(full)
    except OSError:
        pass

    return sorted(matches)


@lru_cache(maxsize=1)
def _get_path_commands() -> frozenset[str]:
    """Get all executable command names from PATH (cached)."""
    commands: set[str] = set()
    path = os.environ.get("PATH", "")

    for directory in path.split(os.pathsep):
        try:
            for entry in os.listdir(directory):
                full_path = os.path.join(directory, entry)
                if os.access(full_path, os.X_OK):
                    commands.add(entry)
        except OSError:
            continue

    return frozenset(commands)
