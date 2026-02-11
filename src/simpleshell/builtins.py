"""Built-in shell commands."""

import os
import readline
import shutil
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simpleshell.shell import Shell

type BuiltinHandler = Callable[[list[str], "Shell"], int]

BUILTINS_HELP: dict[str, str] = {
    "cd": "cd [dir]          - Change directory (default: $HOME)",
    "exit": "exit [code]       - Exit the shell",
    "help": "help              - Show this help message",
    "pwd": "pwd               - Print working directory",
    "export": "export VAR=value  - Set environment variable",
    "unset": "unset VAR         - Unset environment variable",
    "env": "env               - Print all environment variables",
    "alias": "alias [name=cmd]  - Define or list aliases",
    "unalias": "unalias name      - Remove an alias",
    "history": "history           - Show command history",
    "which": "which cmd         - Show path of a command",
    "clear": "clear             - Clear the screen",
    "type": "type cmd          - Show how a command would be interpreted",
    "source": "source file       - Execute commands from a file",
}


def builtin_cd(args: list[str], shell: "Shell") -> int:
    target = args[0] if args else os.path.expanduser("~")
    target = os.path.expanduser(target)
    try:
        os.chdir(target)
    except FileNotFoundError:
        print(f"cd: no such file or directory: {target}", file=sys.stderr)
        return 1
    except NotADirectoryError:
        print(f"cd: not a directory: {target}", file=sys.stderr)
        return 1
    return 0


def builtin_exit(args: list[str], shell: "Shell") -> int:
    code = int(args[0]) if args else 0
    shell.save_history()
    sys.exit(code)


def builtin_help(args: list[str], shell: "Shell") -> int:
    print("simpleShell - built-in commands:\n")
    for line in BUILTINS_HELP.values():
        print(f"  {line}")
    print()
    return 0


def builtin_pwd(args: list[str], shell: "Shell") -> int:
    print(os.getcwd())
    return 0


def builtin_export(args: list[str], shell: "Shell") -> int:
    if not args:
        for key, value in sorted(os.environ.items()):
            print(f"export {key}={value!r}")
        return 0
    for arg in args:
        if "=" in arg:
            name, _, value = arg.partition("=")
            os.environ[name] = value
            if name == "PATH":
                # Invalidate cached PATH commands for tab completion
                from simpleshell.completion import invalidate_path_cache

                invalidate_path_cache()
    return 0


def builtin_unset(args: list[str], shell: "Shell") -> int:
    for name in args:
        os.environ.pop(name, None)
    return 0


def builtin_env(args: list[str], shell: "Shell") -> int:
    for key, value in sorted(os.environ.items()):
        print(f"{key}={value}")
    return 0


def builtin_alias(args: list[str], shell: "Shell") -> int:
    if not args:
        for name, value in sorted(shell.aliases.items()):
            print(f"alias {name}={value!r}")
        return 0
    for arg in args:
        if "=" in arg:
            name, _, value = arg.partition("=")
            shell.aliases[name] = value
        else:
            if arg in shell.aliases:
                print(f"alias {arg}={shell.aliases[arg]!r}")
            else:
                print(f"alias: {arg}: not found", file=sys.stderr)
                return 1
    return 0


def builtin_unalias(args: list[str], shell: "Shell") -> int:
    for name in args:
        if name in shell.aliases:
            del shell.aliases[name]
        else:
            print(f"unalias: {name}: not found", file=sys.stderr)
            return 1
    return 0


def builtin_history(args: list[str], shell: "Shell") -> int:
    length = readline.get_current_history_length()
    for i in range(1, length + 1):
        print(f"  {i}  {readline.get_history_item(i)}")
    return 0


def builtin_which(args: list[str], shell: "Shell") -> int:
    ret = 0
    for name in args:
        path = shutil.which(name)
        if path:
            print(path)
        else:
            print(f"which: no {name} in PATH", file=sys.stderr)
            ret = 1
    return ret


def builtin_clear(args: list[str], shell: "Shell") -> int:
    print("\033[2J\033[H", end="", flush=True)
    return 0


def builtin_type(args: list[str], shell: "Shell") -> int:
    ret = 0
    for name in args:
        match name:
            case n if n in BUILTIN_REGISTRY:
                print(f"{name} is a shell builtin")
            case n if n in shell.aliases:
                print(f"{name} is aliased to `{shell.aliases[n]}'")
            case _:
                path = shutil.which(name)
                if path:
                    print(f"{name} is {path}")
                else:
                    print(f"type: {name}: not found", file=sys.stderr)
                    ret = 1
    return ret


def builtin_source(args: list[str], shell: "Shell") -> int:
    if not args:
        print("source: filename argument required", file=sys.stderr)
        return 1
    try:
        with open(args[0]) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    shell.run_command(line)
    except FileNotFoundError:
        print(f"source: {args[0]}: No such file or directory", file=sys.stderr)
        return 1
    return 0


BUILTIN_REGISTRY: dict[str, BuiltinHandler] = {
    "cd": builtin_cd,
    "exit": builtin_exit,
    "help": builtin_help,
    "pwd": builtin_pwd,
    "export": builtin_export,
    "unset": builtin_unset,
    "env": builtin_env,
    "alias": builtin_alias,
    "unalias": builtin_unalias,
    "history": builtin_history,
    "which": builtin_which,
    "clear": builtin_clear,
    "type": builtin_type,
    "source": builtin_source,
}
