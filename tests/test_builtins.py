"""Tests for the builtins module."""

import os

import pytest

from simpleshell.builtins import (
    BUILTIN_REGISTRY,
    BUILTINS_HELP,
    builtin_alias,
    builtin_cd,
    builtin_env,
    builtin_export,
    builtin_help,
    builtin_history,
    builtin_pwd,
    builtin_source,
    builtin_type,
    builtin_unalias,
    builtin_unset,
    builtin_which,
)
from simpleshell.shell import Shell


@pytest.fixture
def shell():
    return Shell()


class TestBuiltinRegistry:
    def test_all_help_entries_have_handlers(self):
        for name in BUILTINS_HELP:
            assert name in BUILTIN_REGISTRY, f"'{name}' missing from BUILTIN_REGISTRY"

    def test_all_handlers_have_help_entries(self):
        for name in BUILTIN_REGISTRY:
            assert name in BUILTINS_HELP, f"'{name}' in BUILTIN_REGISTRY but not in BUILTINS_HELP"

    def test_handlers_are_callable(self):
        for name, handler in BUILTIN_REGISTRY.items():
            assert callable(handler), f"handler for '{name}' is not callable"


class TestCd:
    def test_cd_to_directory(self, tmp_path, shell):
        target = str(tmp_path)
        result = builtin_cd([target], shell)
        assert result == 0
        assert os.getcwd() == target

    def test_cd_no_args_goes_home(self, shell):
        result = builtin_cd([], shell)
        assert result == 0
        assert os.getcwd() == os.path.expanduser("~")

    def test_cd_tilde(self, shell):
        result = builtin_cd(["~"], shell)
        assert result == 0
        assert os.getcwd() == os.path.expanduser("~")

    def test_cd_nonexistent(self, shell, capsys):
        result = builtin_cd(["/nonexistent_dir_xyz"], shell)
        assert result == 1
        assert "no such file or directory" in capsys.readouterr().err

    def test_cd_to_file(self, tmp_path, shell, capsys):
        f = tmp_path / "afile.txt"
        f.touch()
        result = builtin_cd([str(f)], shell)
        assert result == 1
        assert "not a directory" in capsys.readouterr().err


class TestPwd:
    def test_pwd(self, tmp_path, shell, capsys, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = builtin_pwd([], shell)
        assert result == 0
        assert capsys.readouterr().out.strip() == str(tmp_path)


class TestExport:
    def test_export_set_var(self, shell, monkeypatch):
        monkeypatch.delenv("TEST_SHELL_VAR", raising=False)
        result = builtin_export(["TEST_SHELL_VAR=hello"], shell)
        assert result == 0
        assert os.environ["TEST_SHELL_VAR"] == "hello"

    def test_export_set_with_equals_in_value(self, shell):
        result = builtin_export(["KEY=a=b=c"], shell)
        assert result == 0
        assert os.environ["KEY"] == "a=b=c"

    def test_export_no_args_lists(self, shell, capsys, monkeypatch):
        monkeypatch.setenv("TEST_EXPORT_LIST", "val")
        result = builtin_export([], shell)
        assert result == 0
        output = capsys.readouterr().out
        assert "TEST_EXPORT_LIST" in output

    def test_export_multiple(self, shell):
        builtin_export(["A=1", "B=2"], shell)
        assert os.environ["A"] == "1"
        assert os.environ["B"] == "2"


class TestUnset:
    def test_unset_existing(self, shell, monkeypatch):
        monkeypatch.setenv("TO_UNSET", "value")
        result = builtin_unset(["TO_UNSET"], shell)
        assert result == 0
        assert "TO_UNSET" not in os.environ

    def test_unset_nonexistent(self, shell):
        result = builtin_unset(["NONEXISTENT_VAR_ABC"], shell)
        assert result == 0  # no error for missing vars


class TestEnv:
    def test_env_prints_vars(self, shell, capsys, monkeypatch):
        monkeypatch.setenv("TEST_ENV_VAR", "myval")
        result = builtin_env([], shell)
        assert result == 0
        output = capsys.readouterr().out
        assert "TEST_ENV_VAR=myval" in output

    def test_env_output_sorted(self, shell, capsys, monkeypatch):
        monkeypatch.setenv("ZZZ_VAR", "z")
        monkeypatch.setenv("AAA_VAR", "a")
        builtin_env([], shell)
        output = capsys.readouterr().out
        lines = output.strip().splitlines()
        keys = [line.split("=", 1)[0] for line in lines]
        assert keys == sorted(keys)


class TestAlias:
    def test_define_alias(self, shell):
        result = builtin_alias(["ll=ls -la"], shell)
        assert result == 0
        assert shell.aliases["ll"] == "ls -la"

    def test_list_aliases(self, shell, capsys):
        shell.aliases["ll"] = "ls -la"
        shell.aliases["gs"] = "git status"
        result = builtin_alias([], shell)
        assert result == 0
        output = capsys.readouterr().out
        assert "ll" in output
        assert "gs" in output

    def test_show_specific_alias(self, shell, capsys):
        shell.aliases["ll"] = "ls -la"
        result = builtin_alias(["ll"], shell)
        assert result == 0
        assert "ls -la" in capsys.readouterr().out

    def test_show_nonexistent_alias(self, shell, capsys):
        result = builtin_alias(["nope"], shell)
        assert result == 1
        assert "not found" in capsys.readouterr().err

    def test_multiple_aliases(self, shell):
        builtin_alias(["a=1", "b=2"], shell)
        assert shell.aliases["a"] == "1"
        assert shell.aliases["b"] == "2"


class TestUnalias:
    def test_unalias_existing(self, shell):
        shell.aliases["ll"] = "ls -la"
        result = builtin_unalias(["ll"], shell)
        assert result == 0
        assert "ll" not in shell.aliases

    def test_unalias_nonexistent(self, shell, capsys):
        result = builtin_unalias(["nope"], shell)
        assert result == 1
        assert "not found" in capsys.readouterr().err


class TestHelp:
    def test_help_returns_zero(self, shell):
        assert builtin_help([], shell) == 0

    def test_help_lists_all_builtins(self, shell, capsys):
        builtin_help([], shell)
        output = capsys.readouterr().out
        for name in BUILTINS_HELP:
            assert name in output


class TestHistory:
    def test_history_returns_zero(self, shell):
        assert builtin_history([], shell) == 0


class TestWhich:
    def test_which_existing_command(self, shell, capsys):
        # 'python3' or 'sh' should exist everywhere
        result = builtin_which(["sh"], shell)
        assert result == 0
        output = capsys.readouterr().out.strip()
        assert "sh" in output

    def test_which_nonexistent(self, shell, capsys):
        result = builtin_which(["nonexistent_cmd_xyz"], shell)
        assert result == 1
        assert "no nonexistent_cmd_xyz in PATH" in capsys.readouterr().err

    def test_which_multiple(self, shell, capsys):
        result = builtin_which(["sh", "nonexistent_cmd_xyz"], shell)
        assert result == 1  # returns 1 because one failed


class TestType:
    def test_type_builtin(self, shell, capsys):
        result = builtin_type(["cd"], shell)
        assert result == 0
        assert "shell builtin" in capsys.readouterr().out

    def test_type_alias(self, shell, capsys):
        shell.aliases["ll"] = "ls -la"
        result = builtin_type(["ll"], shell)
        assert result == 0
        assert "aliased" in capsys.readouterr().out

    def test_type_external(self, shell, capsys):
        result = builtin_type(["sh"], shell)
        assert result == 0
        output = capsys.readouterr().out
        assert "sh is /" in output or "sh is " in output

    def test_type_not_found(self, shell, capsys):
        result = builtin_type(["nonexistent_cmd_xyz"], shell)
        assert result == 1
        assert "not found" in capsys.readouterr().err


class TestSource:
    def test_source_file(self, tmp_path, shell, capsys):
        script = tmp_path / "cmds.sh"
        script.write_text("pwd\n")
        result = builtin_source([str(script)], shell)
        assert result == 0

    def test_source_skips_comments(self, tmp_path, shell, capsys):
        script = tmp_path / "cmds.sh"
        script.write_text("# this is a comment\npwd\n")
        result = builtin_source([str(script)], shell)
        assert result == 0
        output = capsys.readouterr().out
        # pwd should have printed something, comment should be skipped
        assert len(output.strip()) > 0

    def test_source_skips_empty_lines(self, tmp_path, shell, capsys):
        script = tmp_path / "cmds.sh"
        script.write_text("\n\npwd\n\n")
        result = builtin_source([str(script)], shell)
        assert result == 0

    def test_source_nonexistent(self, shell, capsys):
        result = builtin_source(["/nonexistent_file_xyz"], shell)
        assert result == 1
        assert "No such file" in capsys.readouterr().err

    def test_source_no_args(self, shell, capsys):
        result = builtin_source([], shell)
        assert result == 1
        assert "filename argument required" in capsys.readouterr().err


class TestExit:
    def test_exit_raises_system_exit(self, shell):
        with pytest.raises(SystemExit) as exc_info:
            from simpleshell.builtins import builtin_exit

            builtin_exit([], shell)
        assert exc_info.value.code == 0

    def test_exit_with_code(self, shell):
        with pytest.raises(SystemExit) as exc_info:
            from simpleshell.builtins import builtin_exit

            builtin_exit(["42"], shell)
        assert exc_info.value.code == 42
