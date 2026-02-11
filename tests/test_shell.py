"""Tests for the Shell class (unit tests for orchestration logic)."""

import os

import pytest

from simpleshell.shell import Shell


@pytest.fixture
def shell():
    return Shell()


class TestShellInit:
    def test_initial_state(self, shell):
        assert shell.aliases == {}
        assert shell.last_exit_code == 0


class TestPrompt:
    def test_prompt_at_home(self, shell, monkeypatch):
        home = os.path.expanduser("~")
        monkeypatch.chdir(home)
        assert shell.get_prompt() == "~ $ "

    def test_prompt_in_subdir(self, shell, monkeypatch):
        home = os.path.expanduser("~")
        # Use a directory that exists under home
        test_dir = os.path.join(home, ".claude")
        if os.path.isdir(test_dir):
            monkeypatch.chdir(test_dir)
            assert shell.get_prompt() == "~/.claude $ "

    def test_prompt_outside_home(self, shell, monkeypatch):
        monkeypatch.chdir("/tmp")
        prompt = shell.get_prompt()
        # /tmp might be a symlink to /private/tmp on macOS
        assert prompt.endswith(" $ ")
        assert "~" not in prompt or prompt.startswith("~/")


class TestSplitCommandList:
    def test_single_command(self):
        result = Shell._split_command_list(["echo", "hello"])
        assert result == [(None, ["echo", "hello"])]

    def test_and_operator(self):
        result = Shell._split_command_list(["cmd1", "&&", "cmd2"])
        assert result == [(None, ["cmd1"]), ("&&", ["cmd2"])]

    def test_or_operator(self):
        result = Shell._split_command_list(["cmd1", "||", "cmd2"])
        assert result == [(None, ["cmd1"]), ("||", ["cmd2"])]

    def test_chain_of_operators(self):
        result = Shell._split_command_list(["a", "&&", "b", "||", "c", "&&", "d"])
        assert result == [
            (None, ["a"]),
            ("&&", ["b"]),
            ("||", ["c"]),
            ("&&", ["d"]),
        ]

    def test_preserves_args(self):
        result = Shell._split_command_list(["cmd1", "-a", "&&", "cmd2", "-b", "-c"])
        assert result == [
            (None, ["cmd1", "-a"]),
            ("&&", ["cmd2", "-b", "-c"]),
        ]

    def test_leading_and_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            Shell._split_command_list(["&&", "cmd"])

    def test_trailing_and_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            Shell._split_command_list(["cmd", "&&"])

    def test_trailing_or_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            Shell._split_command_list(["cmd", "||"])

    def test_double_operator_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            Shell._split_command_list(["cmd1", "&&", "&&", "cmd2"])

    def test_pipe_not_split_here(self):
        # Pipes should NOT be split by _split_command_list
        result = Shell._split_command_list(["cmd1", "|", "cmd2"])
        assert result == [(None, ["cmd1", "|", "cmd2"])]


class TestAliasExpansion:
    def test_simple_alias(self, shell):
        shell.aliases["ll"] = "ls -la"
        result = shell._expand_aliases(["ll"])
        assert result == ["ls", "-la"]

    def test_alias_with_extra_args(self, shell):
        shell.aliases["ll"] = "ls -la"
        result = shell._expand_aliases(["ll", "/tmp"])
        assert result == ["ls", "-la", "/tmp"]

    def test_no_alias(self, shell):
        result = shell._expand_aliases(["ls", "-la"])
        assert result == ["ls", "-la"]

    def test_recursive_alias_stops(self, shell):
        shell.aliases["ls"] = "ls --color"
        result = shell._expand_aliases(["ls"])
        # Should expand once but not loop
        assert result == ["ls", "--color"]

    def test_chained_aliases(self, shell):
        shell.aliases["ll"] = "myls"
        shell.aliases["myls"] = "ls -la"
        result = shell._expand_aliases(["ll"])
        assert result == ["ls", "-la"]

    def test_empty_tokens(self, shell):
        result = shell._expand_aliases([])
        assert result == []


class TestRunCommand:
    def test_builtin_pwd(self, shell, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        shell.run_command("pwd")
        assert str(tmp_path) in capsys.readouterr().out

    def test_empty_command(self, shell, capsys):
        shell.run_command("")
        assert capsys.readouterr().out == ""

    def test_whitespace_command(self, shell, capsys):
        shell.run_command("   ")
        assert capsys.readouterr().out == ""

    def test_command_not_found(self, shell, capsys):
        shell.run_command("nonexistent_command_xyz_123")
        assert "command not found" in capsys.readouterr().err

    def test_exit_code_success(self, shell):
        shell.run_command("true")
        assert shell.last_exit_code == 0

    def test_exit_code_failure(self, shell):
        shell.run_command("false")
        assert shell.last_exit_code != 0

    def test_and_operator_short_circuit(self, shell):
        # false && echo skipped => echo should not run, exit code stays non-zero
        shell.run_command("false && true")
        assert shell.last_exit_code != 0

    def test_and_operator_runs_second(self, shell):
        shell.run_command("true && true")
        assert shell.last_exit_code == 0

    def test_or_operator_fallback(self, shell):
        shell.run_command("false || true")
        assert shell.last_exit_code == 0

    def test_or_operator_skip_on_success(self, shell):
        shell.run_command("true || false")
        assert shell.last_exit_code == 0

    def test_complex_chain_exit_codes(self, shell):
        # false && false || true => skip second false, run true
        shell.run_command("false && false || true")
        assert shell.last_exit_code == 0

    def test_alias_expansion_with_builtin(self, shell, capsys):
        shell.aliases["p"] = "pwd"
        shell.run_command("p")
        # pwd is a builtin, so capsys captures it
        assert len(capsys.readouterr().out.strip()) > 0

    def test_echo_to_file(self, shell, tmp_path):
        outfile = tmp_path / "out.txt"
        shell.run_command(f"echo hello > {outfile}")
        assert outfile.read_text().strip() == "hello"

    def test_var_expansion_to_file(self, shell, tmp_path, monkeypatch):
        monkeypatch.setenv("GREETING", "hello")
        outfile = tmp_path / "out.txt"
        shell.run_command(f"echo $GREETING > {outfile}")
        assert "hello" in outfile.read_text()

    def test_syntax_error(self, shell, capsys):
        shell.run_command("echo 'unterminated")
        assert capsys.readouterr().err != ""
