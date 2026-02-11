"""Tests for the completion module."""

import stat

from simpleshell.builtins import BUILTIN_REGISTRY
from simpleshell.completion import (
    _complete_command,
    _complete_path,
    _get_path_commands,
    invalidate_path_cache,
)


class TestCompletePath:
    def test_complete_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "hello.txt").touch()
        (tmp_path / "help.py").touch()
        result = _complete_path("hel")
        assert "hello.txt" in result
        assert "help.py" in result

    def test_complete_directories_get_slash(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "mydir").mkdir()
        result = _complete_path("my")
        assert "mydir/" in result

    def test_complete_empty_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "afile").touch()
        (tmp_path / "bfile").touch()
        result = _complete_path("")
        assert "afile" in result
        assert "bfile" in result

    def test_complete_no_match(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert _complete_path("zzz_nomatch") == []

    def test_complete_subdirectory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "file1.txt").touch()
        (sub / "file2.txt").touch()
        result = _complete_path("sub/f")
        assert "sub/file1.txt" in result
        assert "sub/file2.txt" in result

    def test_results_sorted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "c.txt").touch()
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()
        result = _complete_path("")
        filenames = [r for r in result if r.endswith(".txt")]
        assert filenames == sorted(filenames)

    def test_nonexistent_dir(self):
        result = _complete_path("/nonexistent_dir_xyz/foo")
        assert result == []


class TestCompleteCommand:
    def test_includes_builtins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _complete_command("cd")
        assert "cd" in result

    def test_all_builtins_completable(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        for name in BUILTIN_REGISTRY:
            result = _complete_command(name)
            assert name in result, f"builtin '{name}' not in completions"

    def test_empty_prefix_includes_builtins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _complete_command("")
        for name in BUILTIN_REGISTRY:
            assert name in result


class TestGetPathCommands:
    def test_returns_frozenset(self):
        invalidate_path_cache()
        result = _get_path_commands()
        assert isinstance(result, frozenset)

    def test_contains_common_commands(self):
        invalidate_path_cache()
        result = _get_path_commands()
        # 'sh' should exist on any unix system
        assert "sh" in result

    def test_cache_invalidation(self):
        result1 = _get_path_commands()
        invalidate_path_cache()
        result2 = _get_path_commands()
        # Both should be valid frozensets (content may be same)
        assert isinstance(result1, frozenset)
        assert isinstance(result2, frozenset)

    def test_custom_path(self, tmp_path, monkeypatch):
        # Create a fake executable in a temp dir
        fake_bin = tmp_path / "my_fake_cmd"
        fake_bin.touch()
        fake_bin.chmod(stat.S_IRWXU)
        monkeypatch.setenv("PATH", str(tmp_path))
        invalidate_path_cache()
        result = _get_path_commands()
        assert "my_fake_cmd" in result
