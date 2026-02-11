#!/usr/bin/env python3
"""simpleShell - A simple shell that can execute commands and display output."""

import glob
import os
import readline
import shlex
import subprocess
import sys

HISTORY_FILE = os.path.expanduser("~/.simpleshell_history")


def load_history():
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass


def save_history():
    readline.write_history_file(HISTORY_FILE)


def expand_globs(tokens):
    """Expand glob patterns in tokens."""
    expanded = []
    for token in tokens:
        if "*" in token or "?" in token:
            matches = glob.glob(token)
            if matches:
                expanded.extend(sorted(matches))
            else:
                expanded.append(token)
        else:
            expanded.append(token)
    return expanded


BUILTINS_HELP = {
    "cd": "cd <dir>     - Change directory",
    "exit": "exit         - Exit the shell",
    "help": "help         - Show this help message",
}


def builtin_cd(args):
    target = args[0] if args else os.path.expanduser("~")
    try:
        os.chdir(target)
    except FileNotFoundError:
        print(f"cd: no such file or directory: {target}", file=sys.stderr)
    except NotADirectoryError:
        print(f"cd: not a directory: {target}", file=sys.stderr)


def builtin_help():
    print("simpleShell - built-in commands:\n")
    for line in BUILTINS_HELP.values():
        print(f"  {line}")
    print()


def run_command(line):
    try:
        tokens = shlex.split(line)
    except ValueError as e:
        print(f"simpleshell: {e}", file=sys.stderr)
        return

    if not tokens:
        return

    tokens = expand_globs(tokens)
    cmd, args = tokens[0], tokens[1:]

    if cmd == "cd":
        builtin_cd(args)
    elif cmd == "exit":
        save_history()
        sys.exit(0)
    elif cmd == "help":
        builtin_help()
    else:
        try:
            subprocess.run(tokens)
        except FileNotFoundError:
            print(f"simpleshell: command not found: {cmd}", file=sys.stderr)


def get_prompt():
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home:
        display = "~"
    elif cwd.startswith(home + "/"):
        display = "~/" + cwd[len(home) + 1:]
    else:
        display = cwd
    return f"{display} $ "


def main():
    load_history()
    readline.set_history_length(1000)

    while True:
        try:
            line = input(get_prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        line = line.strip()
        if not line:
            continue

        run_command(line)

    save_history()


if __name__ == "__main__":
    main()
