"""Tests for the pipeline module."""

import pytest

from simpleshell.pipeline import Command, parse_redirections, split_pipeline


class TestSplitPipeline:
    def test_single_command(self):
        assert split_pipeline(["ls", "-la"]) == [["ls", "-la"]]

    def test_two_commands(self):
        assert split_pipeline(["ls", "|", "grep", "foo"]) == [
            ["ls"],
            ["grep", "foo"],
        ]

    def test_three_commands(self):
        result = split_pipeline(["a", "|", "b", "|", "c"])
        assert result == [["a"], ["b"], ["c"]]

    def test_pipe_with_args(self):
        result = split_pipeline(["ls", "-la", "|", "grep", "-i", "foo", "|", "wc", "-l"])
        assert result == [["ls", "-la"], ["grep", "-i", "foo"], ["wc", "-l"]]

    def test_leading_pipe_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            split_pipeline(["|", "cmd"])

    def test_trailing_pipe_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            split_pipeline(["cmd", "|"])

    def test_double_pipe_error(self):
        with pytest.raises(ValueError, match="syntax error"):
            split_pipeline(["cmd1", "|", "|", "cmd2"])

    def test_single_word(self):
        assert split_pipeline(["echo"]) == [["echo"]]


class TestParseRedirections:
    def test_no_redirections(self):
        cmd = parse_redirections(["echo", "hello"])
        assert cmd.argv == ["echo", "hello"]
        assert cmd.stdin_file is None
        assert cmd.stdout_file is None
        assert cmd.stdout_append is False

    def test_stdout_redirect(self):
        cmd = parse_redirections(["echo", "hello", ">", "out.txt"])
        assert cmd.argv == ["echo", "hello"]
        assert cmd.stdout_file == "out.txt"
        assert cmd.stdout_append is False

    def test_stdout_append(self):
        cmd = parse_redirections(["echo", "hello", ">>", "out.txt"])
        assert cmd.argv == ["echo", "hello"]
        assert cmd.stdout_file == "out.txt"
        assert cmd.stdout_append is True

    def test_stdin_redirect(self):
        cmd = parse_redirections(["cat", "<", "in.txt"])
        assert cmd.argv == ["cat"]
        assert cmd.stdin_file == "in.txt"

    def test_both_redirections(self):
        cmd = parse_redirections(["sort", "<", "in.txt", ">", "out.txt"])
        assert cmd.argv == ["sort"]
        assert cmd.stdin_file == "in.txt"
        assert cmd.stdout_file == "out.txt"

    def test_redirect_before_args(self):
        cmd = parse_redirections([">", "out.txt", "echo", "hello"])
        assert cmd.argv == ["echo", "hello"]
        assert cmd.stdout_file == "out.txt"

    def test_missing_stdout_filename(self):
        with pytest.raises(ValueError, match="syntax error"):
            parse_redirections(["echo", ">"])

    def test_missing_stdin_filename(self):
        with pytest.raises(ValueError, match="syntax error"):
            parse_redirections(["cat", "<"])

    def test_missing_append_filename(self):
        with pytest.raises(ValueError, match="syntax error"):
            parse_redirections(["echo", ">>"])

    def test_only_redirect_no_command(self):
        with pytest.raises(ValueError, match="missing command"):
            parse_redirections([">", "file"])

    def test_last_redirect_wins(self):
        cmd = parse_redirections(["echo", ">", "first.txt", ">", "second.txt"])
        assert cmd.stdout_file == "second.txt"
        assert cmd.stdout_append is False

    def test_append_then_overwrite(self):
        cmd = parse_redirections(["echo", ">>", "a.txt", ">", "b.txt"])
        assert cmd.stdout_file == "b.txt"
        assert cmd.stdout_append is False

    def test_overwrite_then_append(self):
        cmd = parse_redirections(["echo", ">", "a.txt", ">>", "b.txt"])
        assert cmd.stdout_file == "b.txt"
        assert cmd.stdout_append is True


class TestCommandDataclass:
    def test_defaults(self):
        cmd = Command(argv=["ls"])
        assert cmd.stdin_file is None
        assert cmd.stdout_file is None
        assert cmd.stdout_append is False

    def test_full_construction(self):
        cmd = Command(
            argv=["sort"],
            stdin_file="in.txt",
            stdout_file="out.txt",
            stdout_append=True,
        )
        assert cmd.argv == ["sort"]
        assert cmd.stdin_file == "in.txt"
        assert cmd.stdout_file == "out.txt"
        assert cmd.stdout_append is True

    def test_equality(self):
        a = Command(argv=["ls"], stdout_file="f.txt")
        b = Command(argv=["ls"], stdout_file="f.txt")
        assert a == b
