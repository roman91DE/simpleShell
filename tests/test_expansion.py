"""Tests for the expansion module."""

import os

from simpleshell.expansion import expand_globs, expand_tilde, expand_variables


class TestExpandVariables:
    def test_simple_var(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        assert expand_variables("echo $FOO") == "echo bar"

    def test_braced_var(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        assert expand_variables("echo ${FOO}") == "echo bar"

    def test_undefined_var_expands_to_empty(self, monkeypatch):
        monkeypatch.delenv("NONEXISTENT_VAR_XYZ", raising=False)
        assert expand_variables("echo $NONEXISTENT_VAR_XYZ") == "echo "

    def test_undefined_braced_var(self, monkeypatch):
        monkeypatch.delenv("NOPE", raising=False)
        assert expand_variables("echo ${NOPE}end") == "echo end"

    def test_single_quotes_prevent_expansion(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        assert expand_variables("echo '$FOO'") == "echo '$FOO'"

    def test_double_quotes_allow_expansion(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        assert expand_variables('echo "$FOO"') == 'echo "bar"'

    def test_mixed_quotes(self, monkeypatch):
        monkeypatch.setenv("X", "yes")
        result = expand_variables("echo '$X' \"$X\"")
        assert result == "echo '$X' \"yes\""

    def test_adjacent_vars(self, monkeypatch):
        monkeypatch.setenv("A", "hello")
        monkeypatch.setenv("B", "world")
        assert expand_variables("$A$B") == "helloworld"

    def test_var_in_middle_of_word(self, monkeypatch):
        monkeypatch.setenv("NAME", "test")
        assert expand_variables("file_${NAME}.txt") == "file_test.txt"

    def test_bare_dollar_at_end(self):
        assert expand_variables("echo $") == "echo $"

    def test_dollar_followed_by_number(self):
        # $1 doesn't match [a-zA-Z_], so $ stays literal
        assert expand_variables("echo $1") == "echo $1"

    def test_dollar_followed_by_special(self):
        assert expand_variables("echo $!") == "echo $!"

    def test_unterminated_brace(self):
        # Unterminated ${...  is kept literal
        assert expand_variables("echo ${FOO") == "echo ${FOO"

    def test_backslash_escaping(self, monkeypatch):
        monkeypatch.setenv("FOO", "bar")
        result = expand_variables("echo \\$FOO")
        assert "$FOO" in result

    def test_empty_string(self):
        assert expand_variables("") == ""

    def test_no_vars(self):
        assert expand_variables("echo hello world") == "echo hello world"

    def test_var_with_underscore(self, monkeypatch):
        monkeypatch.setenv("MY_VAR_123", "value")
        assert expand_variables("$MY_VAR_123") == "value"

    def test_home_var(self, monkeypatch):
        monkeypatch.setenv("HOME", "/Users/test")
        assert expand_variables("cd $HOME") == "cd /Users/test"


class TestExpandGlobs:
    def test_no_glob_unchanged(self):
        assert expand_globs(["echo", "hello"]) == ["echo", "hello"]

    def test_star_glob_matches(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "foo.py").touch()
        (tmp_path / "bar.py").touch()
        (tmp_path / "baz.txt").touch()
        result = expand_globs(["ls", "*.py"])
        assert result == ["ls", "bar.py", "foo.py"]

    def test_question_glob_matches(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a1.txt").touch()
        (tmp_path / "a2.txt").touch()
        (tmp_path / "b1.txt").touch()
        result = expand_globs(["ls", "a?.txt"])
        assert result == ["ls", "a1.txt", "a2.txt"]

    def test_no_match_keeps_pattern(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert expand_globs(["ls", "*.nonexistent"]) == ["ls", "*.nonexistent"]

    def test_operators_not_expanded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert expand_globs(["|"]) == ["|"]
        assert expand_globs([">"]) == [">"]
        assert expand_globs([">>"]) == [">>"]
        assert expand_globs(["<"]) == ["<"]
        assert expand_globs(["&&"]) == ["&&"]
        assert expand_globs(["||"]) == ["||"]

    def test_multiple_globs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "a.py").touch()
        (tmp_path / "b.txt").touch()
        result = expand_globs(["*.py", "*.txt"])
        assert result == ["a.py", "b.txt"]

    def test_glob_results_sorted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "c.py").touch()
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()
        result = expand_globs(["*.py"])
        assert result == ["a.py", "b.py", "c.py"]


class TestExpandTilde:
    def test_tilde_alone(self):
        result = expand_tilde(["~"])
        assert result == [os.path.expanduser("~")]

    def test_tilde_with_path(self):
        result = expand_tilde(["~/documents"])
        assert result == [os.path.expanduser("~/documents")]

    def test_no_tilde_unchanged(self):
        assert expand_tilde(["/usr/bin"]) == ["/usr/bin"]

    def test_tilde_not_at_start_unchanged(self):
        assert expand_tilde(["foo~bar"]) == ["foo~bar"]

    def test_multiple_tokens(self):
        result = expand_tilde(["~", "/tmp", "~/foo"])
        home = os.path.expanduser("~")
        assert result == [home, "/tmp", f"{home}/foo"]

    def test_empty_list(self):
        assert expand_tilde([]) == []
