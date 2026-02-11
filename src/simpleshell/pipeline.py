"""Parse and execute command pipelines with I/O redirection."""

import subprocess
import sys
from dataclasses import dataclass

from simpleshell.tokenizer import PIPE


@dataclass
class Command:
    """A single command in a pipeline with its redirections."""

    argv: list[str]
    stdin_file: str | None = None
    stdout_file: str | None = None
    stdout_append: bool = False


def split_pipeline(tokens: list[str]) -> list[list[str]]:
    """Split tokens on '|' into segments.

    Example: ['ls', '|', 'grep', 'foo'] -> [['ls'], ['grep', 'foo']]

    Raises ValueError if pipeline syntax is invalid.
    """
    segments: list[list[str]] = []
    current: list[str] = []

    for token in tokens:
        if token == PIPE:
            if not current:
                raise ValueError("syntax error near unexpected token `|'")
            segments.append(current)
            current = []
        else:
            current.append(token)

    if not current:
        raise ValueError("syntax error near unexpected token `|'")
    segments.append(current)

    return segments


def parse_redirections(segment: list[str]) -> Command:
    """Extract redirection operators from a command segment.

    Uses match/case to dispatch on operator tokens.
    Raises ValueError on missing filenames.
    """
    argv: list[str] = []
    stdin_file: str | None = None
    stdout_file: str | None = None
    stdout_append: bool = False

    i = 0
    while i < len(segment):
        token = segment[i]

        match token:
            case "<":
                if i + 1 >= len(segment):
                    raise ValueError("syntax error near unexpected token `newline'")
                stdin_file = segment[i + 1]
                i += 2
            case ">" | ">>":
                if i + 1 >= len(segment):
                    raise ValueError("syntax error near unexpected token `newline'")
                stdout_file = segment[i + 1]
                stdout_append = token == ">>"
                i += 2
            case _:
                argv.append(token)
                i += 1

    if not argv:
        raise ValueError("syntax error: missing command")

    return Command(
        argv=argv,
        stdin_file=stdin_file,
        stdout_file=stdout_file,
        stdout_append=stdout_append,
    )


def execute_pipeline(commands: list[Command]) -> int:
    """Execute a pipeline of commands, returning the last exit code."""
    if len(commands) == 1:
        return _execute_single(commands[0])
    return _execute_multi(commands)


def _execute_single(cmd: Command) -> int:
    """Execute a single command (no pipes)."""
    try:
        stdin_fh, stdout_fh = _open_redirects(cmd)
    except FileNotFoundError:
        return 1

    try:
        result = subprocess.run(cmd.argv, stdin=stdin_fh, stdout=stdout_fh)
        return result.returncode
    except FileNotFoundError:
        print(f"simpleshell: command not found: {cmd.argv[0]}", file=sys.stderr)
        return 127
    finally:
        if stdin_fh:
            stdin_fh.close()
        if stdout_fh:
            stdout_fh.close()


def _execute_multi(commands: list[Command]) -> int:
    """Execute a multi-command pipeline with Popen chaining."""
    processes: list[subprocess.Popen] = []
    opened_files: list = []

    try:
        for i, cmd in enumerate(commands):
            stdin_source = None
            stdout_dest = None

            # First command: may have stdin redirection
            if i == 0:
                if cmd.stdin_file:
                    fh = open(cmd.stdin_file)  # noqa: SIM115
                    opened_files.append(fh)
                    stdin_source = fh
            else:
                stdin_source = processes[i - 1].stdout

            # Last command: may have stdout redirection
            if i == len(commands) - 1:
                if cmd.stdout_file:
                    mode = "a" if cmd.stdout_append else "w"
                    fh = open(cmd.stdout_file, mode)  # noqa: SIM115
                    opened_files.append(fh)
                    stdout_dest = fh
            else:
                stdout_dest = subprocess.PIPE

            proc = subprocess.Popen(cmd.argv, stdin=stdin_source, stdout=stdout_dest)
            processes.append(proc)

            # Close previous process's stdout in parent so EOF propagates
            if i > 0 and processes[i - 1].stdout:
                processes[i - 1].stdout.close()

        for proc in processes:
            proc.wait()

        return processes[-1].returncode

    except FileNotFoundError as e:
        print(f"simpleshell: command not found: {e.filename}", file=sys.stderr)
        for proc in processes:
            proc.kill()
            proc.wait()
        return 127

    finally:
        for fh in opened_files:
            fh.close()


def _open_redirects(cmd: Command) -> tuple:
    """Open file handles for redirections. Returns (stdin_fh, stdout_fh)."""
    stdin_fh = None
    stdout_fh = None

    if cmd.stdin_file:
        try:
            stdin_fh = open(cmd.stdin_file)  # noqa: SIM115
        except FileNotFoundError:
            print(
                f"simpleshell: {cmd.stdin_file}: No such file or directory",
                file=sys.stderr,
            )
            raise

    if cmd.stdout_file:
        mode = "a" if cmd.stdout_append else "w"
        stdout_fh = open(cmd.stdout_file, mode)  # noqa: SIM115

    return stdin_fh, stdout_fh
