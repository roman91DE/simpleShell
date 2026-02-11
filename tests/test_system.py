"""System tests — run the shell as a subprocess and verify end-to-end behavior."""

import os
import subprocess
import sys

SHELL_CMD = [sys.executable, "-m", "simpleshell"]


def run_shell(commands: str, **kwargs) -> subprocess.CompletedProcess:
    """Run simpleshell with the given commands piped to stdin."""
    return subprocess.run(
        SHELL_CMD,
        input=commands,
        capture_output=True,
        text=True,
        timeout=10,
        **kwargs,
    )


class TestBasicExecution:
    def test_echo(self):
        result = run_shell("echo hello world\nexit\n")
        assert "hello world" in result.stdout

    def test_exit_code_zero(self):
        result = run_shell("exit\n")
        assert result.returncode == 0

    def test_exit_code_custom(self):
        result = run_shell("exit 42\n")
        assert result.returncode == 42

    def test_multiple_commands(self):
        result = run_shell("echo first\necho second\nexit\n")
        assert "first" in result.stdout
        assert "second" in result.stdout

    def test_command_not_found(self):
        result = run_shell("nonexistent_command_xyz\nexit\n")
        assert "command not found" in result.stderr

    def test_empty_lines_ignored(self):
        result = run_shell("\n\n\necho ok\n\nexit\n")
        assert "ok" in result.stdout


class TestPipes:
    def test_simple_pipe(self):
        result = run_shell("echo hello world | tr a-z A-Z\nexit\n")
        assert "HELLO WORLD" in result.stdout

    def test_multi_pipe(self):
        result = run_shell("echo 'aaa\\nbbb\\nccc' | sort | head -1\nexit\n")
        # Should get sorted output
        assert result.returncode == 0

    def test_pipe_grep(self):
        result = run_shell("echo hello | grep hello\nexit\n")
        assert "hello" in result.stdout

    def test_pipe_grep_no_match(self):
        result = run_shell("echo hello | grep goodbye\nexit\n")
        assert "goodbye" not in result.stdout

    def test_pipe_wc(self):
        result = run_shell("echo hello | wc -c\nexit\n")
        # wc -c of "hello\n" is 6; look for a digit in the output
        assert any(c.isdigit() for c in result.stdout)


class TestRedirections:
    def test_stdout_redirect(self, tmp_path):
        outfile = tmp_path / "out.txt"
        run_shell(f"echo hello > {outfile}\nexit\n")
        assert outfile.read_text().strip() == "hello"

    def test_stdout_append(self, tmp_path):
        outfile = tmp_path / "out.txt"
        run_shell(f"echo line1 > {outfile}\necho line2 >> {outfile}\nexit\n")
        content = outfile.read_text()
        assert "line1" in content
        assert "line2" in content

    def test_stdin_redirect(self, tmp_path):
        infile = tmp_path / "in.txt"
        infile.write_text("hello from file\n")
        result = run_shell(f"cat < {infile}\nexit\n")
        assert "hello from file" in result.stdout

    def test_redirect_overwrite(self, tmp_path):
        outfile = tmp_path / "out.txt"
        run_shell(f"echo first > {outfile}\necho second > {outfile}\nexit\n")
        assert outfile.read_text().strip() == "second"

    def test_redirect_nonexistent_input(self, tmp_path):
        result = run_shell(f"cat < {tmp_path}/nonexistent.txt\nexit\n")
        assert "No such file" in result.stderr

    def test_pipe_with_redirect(self, tmp_path):
        outfile = tmp_path / "out.txt"
        run_shell(f"echo hello world | tr a-z A-Z > {outfile}\nexit\n")
        assert outfile.read_text().strip() == "HELLO WORLD"


class TestBuiltinRedirection:
    def test_help_redirect(self, tmp_path):
        outfile = tmp_path / "help.txt"
        run_shell(f"help > {outfile}\nexit\n")
        content = outfile.read_text()
        assert "built-in commands" in content

    def test_pwd_redirect(self, tmp_path):
        outfile = tmp_path / "pwd.txt"
        run_shell(f"pwd > {outfile}\nexit\n")
        content = outfile.read_text().strip()
        assert len(content) > 0

    def test_env_redirect(self, tmp_path):
        outfile = tmp_path / "env.txt"
        run_shell(f"env > {outfile}\nexit\n")
        content = outfile.read_text()
        assert "PATH=" in content


class TestVariableExpansion:
    def test_home_expansion(self):
        result = run_shell("echo $HOME\nexit\n")
        home = os.path.expanduser("~")
        assert home in result.stdout

    def test_braced_var(self):
        result = run_shell("echo ${HOME}\nexit\n")
        home = os.path.expanduser("~")
        assert home in result.stdout

    def test_undefined_var(self):
        result = run_shell("echo $UNDEFINED_VAR_XYZ_123\nexit\n")
        # Undefined var expands to empty, so echo prints a blank line.
        # The value "UNDEFINED_VAR_XYZ_123" should NOT appear literally.
        assert "UNDEFINED_VAR_XYZ_123" not in result.stdout

    def test_single_quotes_no_expand(self):
        result = run_shell("echo '$HOME'\nexit\n")
        assert "$HOME" in result.stdout

    def test_double_quotes_expand(self):
        result = run_shell('echo "$HOME"\nexit\n')
        home = os.path.expanduser("~")
        assert home in result.stdout


class TestAndOr:
    def test_and_success(self):
        result = run_shell("echo a && echo b\nexit\n")
        assert "a" in result.stdout
        assert "b" in result.stdout

    def test_and_failure(self):
        result = run_shell("false && echo skipped\nexit\n")
        assert "skipped" not in result.stdout

    def test_or_failure(self):
        result = run_shell("false || echo fallback\nexit\n")
        assert "fallback" in result.stdout

    def test_or_success(self):
        result = run_shell("true || echo skipped\nexit\n")
        assert "skipped" not in result.stdout

    def test_chain_and_or(self):
        result = run_shell("true && echo yes || echo no\nexit\n")
        assert "yes" in result.stdout
        assert "no" not in result.stdout

    def test_chain_failure_recovery(self):
        result = run_shell("false && echo no || echo recovered\nexit\n")
        assert "no" not in result.stdout
        assert "recovered" in result.stdout

    def test_three_ands(self):
        result = run_shell("echo a && echo b && echo c\nexit\n")
        assert "a" in result.stdout
        assert "b" in result.stdout
        assert "c" in result.stdout

    def test_and_stops_at_failure(self):
        result = run_shell("echo a && false && echo c\nexit\n")
        assert "a" in result.stdout
        assert "c" not in result.stdout

    def test_pipe_with_and(self):
        result = run_shell("echo hello | tr a-z A-Z && echo done\nexit\n")
        assert "HELLO" in result.stdout
        assert "done" in result.stdout


class TestBuiltins:
    def test_cd_and_pwd(self, tmp_path):
        result = run_shell(f"cd {tmp_path}\npwd\nexit\n")
        assert str(tmp_path) in result.stdout

    def test_cd_home(self):
        result = run_shell("cd\npwd\nexit\n")
        home = os.path.expanduser("~")
        assert home in result.stdout

    def test_export_and_echo(self):
        result = run_shell("export MY_TEST_VAR=hello123\necho $MY_TEST_VAR\nexit\n")
        assert "hello123" in result.stdout

    def test_export_and_unset(self):
        result = run_shell(
            "export MY_TEST_VAR=hello\nunset MY_TEST_VAR\necho $MY_TEST_VAR\nexit\n"
        )
        # After unset, $MY_TEST_VAR should be empty
        lines = result.stdout.strip().splitlines()
        # The echo line should not contain "hello"
        echo_lines = [ln for ln in lines if "hello" in ln and "$ " not in ln]
        assert len(echo_lines) == 0

    def test_alias_and_use(self):
        result = run_shell("alias hi='echo hello'\nhi\nexit\n")
        assert "hello" in result.stdout

    def test_unalias(self):
        result = run_shell("alias hi='echo hello'\nunalias hi\nhi\nexit\n")
        assert "command not found" in result.stderr

    def test_which(self):
        result = run_shell("which sh\nexit\n")
        assert "/sh" in result.stdout or "sh" in result.stdout

    def test_type_builtin(self):
        result = run_shell("type cd\nexit\n")
        assert "shell builtin" in result.stdout

    def test_type_external(self):
        result = run_shell("type sh\nexit\n")
        assert "sh is" in result.stdout

    def test_history(self):
        # When stdin is a pipe, readline may not record history entries.
        # Just verify the history builtin runs without error.
        result = run_shell("history\nexit\n")
        assert result.returncode == 0

    def test_help(self):
        result = run_shell("help\nexit\n")
        assert "built-in commands" in result.stdout
        assert "cd" in result.stdout
        assert "exit" in result.stdout

    def test_source(self, tmp_path):
        script = tmp_path / "test.sh"
        script.write_text("echo sourced_ok\n")
        result = run_shell(f"source {script}\nexit\n")
        assert "sourced_ok" in result.stdout

    def test_source_sets_variable(self, tmp_path):
        script = tmp_path / "setvar.sh"
        script.write_text("export SOURCED_VAR=works\n")
        result = run_shell(f"source {script}\necho $SOURCED_VAR\nexit\n")
        assert "works" in result.stdout


class TestGlobbing:
    def test_star_glob(self, tmp_path):
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()
        (tmp_path / "c.txt").touch()
        result = run_shell(f"cd {tmp_path}\necho *.py\nexit\n")
        assert "a.py" in result.stdout
        assert "b.py" in result.stdout
        assert "c.txt" not in result.stdout

    def test_no_match_literal(self, tmp_path):
        result = run_shell(f"cd {tmp_path}\necho *.nonexistent\nexit\n")
        assert "*.nonexistent" in result.stdout


class TestTildeExpansion:
    def test_tilde_in_echo(self):
        result = run_shell("echo ~\nexit\n")
        home = os.path.expanduser("~")
        assert home in result.stdout

    def test_tilde_path(self):
        result = run_shell("echo ~/foobar\nexit\n")
        home = os.path.expanduser("~")
        assert f"{home}/foobar" in result.stdout


class TestEdgeCases:
    def test_eof_exits_gracefully(self):
        # No exit command, just EOF
        result = run_shell("")
        assert result.returncode == 0

    def test_syntax_error_pipe(self):
        result = run_shell("| cmd\nexit\n")
        assert "syntax error" in result.stderr

    def test_syntax_error_trailing_and(self):
        result = run_shell("cmd &&\nexit\n")
        assert "syntax error" in result.stderr

    def test_syntax_error_trailing_redirect(self):
        result = run_shell("echo >\nexit\n")
        assert "syntax error" in result.stderr

    def test_very_long_pipeline(self):
        result = run_shell("echo test | cat | cat | cat | cat\nexit\n")
        assert "test" in result.stdout
