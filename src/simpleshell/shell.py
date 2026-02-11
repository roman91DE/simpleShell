"""Main shell loop: prompt, read, parse, dispatch, repeat."""

import contextlib
import os
import readline
import sys

from simpleshell.builtins import BUILTIN_REGISTRY
from simpleshell.completion import setup_completion
from simpleshell.expansion import expand_globs, expand_tilde, expand_variables
from simpleshell.pipeline import execute_pipeline, parse_redirections, split_pipeline
from simpleshell.tokenizer import tokenize

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
        5. Expand aliases (first token)
        6. Split on pipes
        7. Parse redirections per segment
        8. Check if single builtin
        9. Execute pipeline
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

        # 5. Alias expansion
        tokens = self._expand_aliases(tokens)

        # 6. Split pipeline
        try:
            segments = split_pipeline(tokens)
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            return

        # 7. Parse redirections
        try:
            commands = [parse_redirections(seg) for seg in segments]
        except ValueError as e:
            print(f"simpleshell: {e}", file=sys.stderr)
            return

        # 8. Builtin check (single command, non-piped only)
        if len(commands) == 1:
            cmd = commands[0]
            if cmd.argv[0] in BUILTIN_REGISTRY:
                self._run_builtin(cmd)
                return

        # 9. Execute external pipeline
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
