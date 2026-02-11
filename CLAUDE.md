# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

simpleShell is a minimal interactive shell written in Python using only the standard library. It supports external command execution, file globbing, built-in commands (`cd`, `exit`, `help`), and persistent command history via readline.

## Running

```bash
python3 simpleshell.py
```

## Constraints

- **Standard library only** — no third-party dependencies. The project has no requirements.txt, setup.py, or tests.
- Single-file implementation (`simpleshell.py`).

## Architecture

The shell loop lives in `main()` → `input()` → `run_command()`:

1. **Tokenization** — `shlex.split` handles quoting/escaping
2. **Glob expansion** — `expand_globs()` expands `*`/`?` patterns in tokens before dispatch
3. **Dispatch** — built-in commands (`cd`, `exit`, `help`) are handled in-process; everything else goes to `subprocess.run`
4. **History** — `readline` provides up/down arrow navigation; history persists to `~/.simpleshell_history`

New built-in commands should be added as functions and wired into the `if/elif` chain in `run_command()`, with a corresponding entry in `BUILTINS_HELP`.
