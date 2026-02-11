"""Main shell loop: prompt, read, parse, dispatch, repeat."""

import contextlib
import os
import readline
import sys

from simpleshell.builtins import BUILTIN_REGISTRY
from simpleshell.completion import setup_completion
from simpleshell.expansion import expand_globs, expand_tilde, expand_variables
from simpleshell.pipeline import execute_pipeline, parse_redirections, split_pipeline
from simpleshell.tokenizer import AND, OR, tokenize

HISTORY_FILE = os.path.expanduser("~/.simpleshell_history")


class Shell:
    """Shell state and main loop."""

    def __init__(self) -> None:
        self.aliases: dict[str, str] = {}
        self.last_exit_code: int = 0

    def load_history(self) -> None:
        with contextlib.suppress(FileNotFoundError, PermissionError, OSError):
            readline.read_history_file(HISTORY_FILE)

    def save_history(self) -> None:
        with contextlib.suppress(PermissionError, OSError):
            readline.write_history_file(HISTORY_FILE)

    def get_prompt(self) -> str:
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if cwd == home:
            display = "~"
        elif cwd.startswith(home + "/"):
            display = "~/" + cwd[len(home) + 1 :]
        else:
            display = cwd
        return f"{display} $ "

    def run_command(self, line: str) -> None:
        """Full processing pipeline:

        1. Expand environment variables ($VAR, ${VAR})
        2. Tokenize (shlex-based, operator-aware)
        3. Expand tilde (~)
        4. Expand globs (* ?)
        5. Expand aliases (first token of each command list segment)
        6. Split on && / || (command list operators)
        7. For each segment: split on pipes, parse redirections, execute
        """
        # 1. Variable expansion on raw string (respects quoting)
        line = expand_variables(line)

        # 2. Tokenize
        try:
            tokens = tokenize(line)
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            return

        if not tokens:
            return

        # 3. Tilde expansion
        tokens = expand_tilde(tokens)

        # 4. Glob expansion
        tokens = expand_globs(tokens)

        # 5-7. Split on && / || and execute each pipeline conditionally
        try:
            cmd_list = self._split_command_list(tokens)
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            return

        for operator, segment_tokens in cmd_list:
            # Check condition from previous pipeline
            match operator:
                case "&&" if self.last_exit_code != 0:
                    continue
                case "||" if self.last_exit_code == 0:
                    continue

            # Alias expansion per segment
            segment_tokens = self._expand_aliases(segment_tokens)

            self._execute_segment(segment_tokens)

    @staticmethod
    def _split_command_list(tokens: list[str]) -> list[tuple[str | None, list[str]]]:
        """Split tokens on && and || into (operator, segment) pairs.

        Returns [(None, first_segment), ("&&", second_segment), ("||", third), ...].
        The first segment always has operator=None.
        """
        result: list[tuple[str | None, list[str]]] = []
        current: list[str] = []
        pending_op: str | None = None

        for token in tokens:
            if token in (AND, OR):
                if not current:
                    raise ValueError(f"syntax error near unexpected token `{token}'")
                result.append((pending_op, current))
                pending_op = token
                current = []
            else:
                current.append(token)

        if not current:
            op = pending_op or "newline"
            raise ValueError(f"syntax error near unexpected token `{op}'")
        result.append((pending_op, current))

        return result

    def _execute_segment(self, tokens: list[str]) -> None:
        """Execute a single pipeline segment (everything between && / ||)."""
        try:
            segments = split_pipeline(tokens)
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            self.last_exit_code = 2
            return

        try:
            commands = [parse_redirections(seg) for seg in segments]
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            self.last_exit_code = 2
            return

        # Builtin check (single command, non-piped only)
        if len(commands) == 1:
            cmd = commands[0]
            if cmd.argv[0] in BUILTIN_REGISTRY:
                self._run_builtin(cmd)
                return

        self.last_exit_code = execute_pipeline(commands)

    def _run_builtin(self, cmd) -> None:
        """Run a builtin command, handling stdout redirection."""
        old_stdout = None
        fh = None
        if cmd.stdout_file:
            mode = "a" if cmd.stdout_append else "w"
            fh = open(cmd.stdout_file, mode)  # noqa: SIM115
            old_stdout = sys.stdout
            sys.stdout = fh
        try:
            handler = BUILTIN_REGISTRY[cmd.argv[0]]
            self.last_exit_code = handler(cmd.argv[1:], self)
        finally:
            if old_stdout is not None:
                sys.stdout = old_stdout
            if fh:
                fh.close()

    def _expand_aliases(self, tokens: list[str]) -> list[str]:
        """Expand aliases in the first token, with loop detection."""
        seen: set[str] = set()
        while tokens and tokens[0] in self.aliases and tokens[0] not in seen:
            name = tokens[0]
            seen.add(name)
            alias_value = self.aliases[name]
            try:
                alias_tokens = tokenize(alias_value)
            except ValueError:
                break
            tokens = alias_tokens + tokens[1:]
        return tokens

    def run(self) -> None:
        """Main shell loop."""
        self.load_history()
        readline.set_history_length(1000)
        setup_completion()

        while True:
            try:
                line = input(self.get_prompt())
            except (EOFError, KeyboardInterrupt):
                print()
                break

            line = line.strip()
            if not line or line.startswith("#"):
                continue

            self.run_command(line)

        self.save_history()


def main() -> None:
    """Entry point."""
    shell = Shell()
    shell.run()
