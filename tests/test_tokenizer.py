"""Tests for the tokenizer module."""

import pytest

from simpleshell.tokenizer import tokenize


class TestBasicTokenization:
    def test_simple_command(self):
        assert tokenize("echo hello") == ["echo", "hello"]

    def test_multiple_args(self):
        assert tokenize("ls -la /tmp") == ["ls", "-la", "/tmp"]

    def test_empty_string(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   ") == []

    def test_single_word(self):
        assert tokenize("ls") == ["ls"]

    def test_preserves_paths(self):
        assert tokenize("cat /usr/local/bin/foo") == ["cat", "/usr/local/bin/foo"]

    def test_preserves_dotfiles(self):
        assert tokenize("ls .hidden") == ["ls", ".hidden"]

    def test_preserves_flags_with_equals(self):
        assert tokenize("cmd --flag=value") == ["cmd", "--flag=value"]


class TestQuoting:
    def test_double_quotes(self):
        assert tokenize('echo "hello world"') == ["echo", "hello world"]

    def test_single_quotes(self):
        assert tokenize("echo 'hello world'") == ["echo", "hello world"]

    def test_mixed_quotes(self):
        assert tokenize("""echo "it's fine" """) == ["echo", "it's fine"]

    def test_escaped_space(self):
        assert tokenize(r"echo hello\ world") == ["echo", "hello world"]

    def test_empty_quotes(self):
        assert tokenize('echo ""') == ["echo", ""]

    def test_adjacent_quoted_strings(self):
        assert tokenize("echo 'foo''bar'") == ["echo", "foobar"]


class TestOperators:
    def test_pipe(self):
        assert tokenize("ls | grep foo") == ["ls", "|", "grep", "foo"]

    def test_redirect_out(self):
        assert tokenize("echo hello > file.txt") == ["echo", "hello", ">", "file.txt"]

    def test_redirect_append(self):
        assert tokenize("echo hello >> file.txt") == ["echo", "hello", ">>", "file.txt"]

    def test_redirect_in(self):
        assert tokenize("cat < file.txt") == ["cat", "<", "file.txt"]

    def test_and_operator(self):
        assert tokenize("cmd1 && cmd2") == ["cmd1", "&&", "cmd2"]

    def test_or_operator(self):
        assert tokenize("cmd1 || cmd2") == ["cmd1", "||", "cmd2"]

    def test_pipe_adjacent_to_word(self):
        assert tokenize("ls|grep foo") == ["ls", "|", "grep", "foo"]

    def test_redirect_adjacent_to_word(self):
        assert tokenize("echo foo>bar") == ["echo", "foo", ">", "bar"]

    def test_redirect_in_adjacent(self):
        assert tokenize("cat<file.txt") == ["cat", "<", "file.txt"]

    def test_multiple_pipes(self):
        assert tokenize("a | b | c") == ["a", "|", "b", "|", "c"]

    def test_combined_operators(self):
        tokens = tokenize("cmd1 | cmd2 && cmd3 || cmd4")
        assert tokens == ["cmd1", "|", "cmd2", "&&", "cmd3", "||", "cmd4"]


class TestOperatorMerging:
    def test_spaced_append_merges(self):
        # Two consecutive > tokens merge into >>
        assert tokenize("echo hello >> file") == ["echo", "hello", ">>", "file"]

    def test_and_merges(self):
        assert tokenize("a && b") == ["a", "&&", "b"]

    def test_or_merges(self):
        assert tokenize("a || b") == ["a", "||", "b"]

    def test_single_pipe_stays(self):
        assert tokenize("a | b") == ["a", "|", "b"]


class TestSpecialCharactersInWords:
    def test_glob_star(self):
        assert tokenize("ls *.py") == ["ls", "*.py"]

    def test_glob_question(self):
        assert tokenize("ls file?.txt") == ["ls", "file?.txt"]

    def test_dollar_in_word(self):
        assert tokenize("echo $HOME") == ["echo", "$HOME"]

    def test_braces_in_word(self):
        assert tokenize("echo ${VAR}") == ["echo", "${VAR}"]

    def test_tilde(self):
        assert tokenize("cd ~/projects") == ["cd", "~/projects"]

    def test_comma_in_word(self):
        assert tokenize("echo a,b,c") == ["echo", "a,b,c"]

    def test_colon_in_word(self):
        assert tokenize("echo /usr/bin:/usr/local/bin") == [
            "echo",
            "/usr/bin:/usr/local/bin",
        ]

    def test_at_sign(self):
        assert tokenize("echo user@host") == ["echo", "user@host"]


class TestErrorHandling:
    def test_unmatched_single_quote(self):
        with pytest.raises(ValueError):
            tokenize("echo 'unterminated")

    def test_unmatched_double_quote(self):
        with pytest.raises(ValueError):
            tokenize('echo "unterminated')
