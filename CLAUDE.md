# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

simpleShell is a minimal interactive shell written in Python (3.12+) using only the standard library. Supports pipelines, I/O redirection, environment variable expansion, glob expansion, tab completion, aliases, and persistent command history.

## Running

```bash
uv run simpleshell
```

## Development

```bash
uv run ruff check src/
uv run ruff format src/
```

## Constraints

- **Standard library only** at runtime — no third-party dependencies.
- Dev dependency: ruff (linting/formatting).
- Python >= 3.12 required (uses match/case, modern type syntax).

## Architecture

`src/simpleshell/` package with these modules:

- **shell.py** — `Shell` class: main loop, prompt, orchestrates the processing pipeline
- **tokenizer.py** — Custom `shlex`-based tokenizer that treats `|`, `>`, `<` as operators
- **expansion.py** — Environment variable expansion (`$VAR`, `${VAR}`), glob and tilde expansion
- **pipeline.py** — Pipeline splitting, redirection parsing, `subprocess.Popen` execution
- **builtins.py** — All builtin commands with `BUILTIN_REGISTRY` dispatch table
- **completion.py** — Readline tab completion for commands and paths

### Processing Pipeline (in `Shell.run_command`)

1. `expand_variables(line)` — `$VAR` expansion respecting quotes
2. `tokenize(line)` — shlex + operator-aware splitting
3. `expand_tilde(tokens)` — `~` to home directory
4. `expand_globs(tokens)` — `*` and `?` patterns
5. `_expand_aliases(tokens)` — alias substitution with loop detection
6. `split_pipeline(tokens)` — split on `|`
7. `parse_redirections(segment)` — extract `>`, `>>`, `<` per command
8. Builtin check (single non-piped command only)
9. `execute_pipeline(commands)` — `subprocess.Popen` chain

### Adding a New Builtin

1. Add handler function in `builtins.py`: `def builtin_foo(args: list[str], shell: "Shell") -> int`
2. Add to `BUILTIN_REGISTRY` dict
3. Add to `BUILTINS_HELP` dict
