"""
The boundary the local tools keep: nothing outside the root, nothing ignored
written or deleted, no git options smuggled in as paths, no SQLite writes
from read-query and no other database files (card #983).
"""

import os
import sqlite3
import subprocess
import shutil

import pytest

from tools.direct_tools import FilesystemToolProvider, GitToolProvider, SQLiteToolProvider
from tools.github_tool import repo_url


@pytest.fixture
def layout(tmp_path):
    """root/ with a file, a .env and a .git, beside a sibling whose name starts like it"""
    root = tmp_path / "j4ne"
    sibling = tmp_path / "j4ne-evil"
    root.mkdir()
    sibling.mkdir()
    (root / "notes.txt").write_text("hello", encoding="utf-8")
    (root / ".env").write_text("API_KEY=secret", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]", encoding="utf-8")
    (sibling / "secret.txt").write_text("sibling secret", encoding="utf-8")
    return root, sibling


def run(provider, name, **args):
    return provider.tools[name].execute(**args)


class TestFilesystemRoot:
    def test_reads_inside_root(self, layout):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert run(fs, "filesystem.read-file", path="notes.txt") == {"content": "hello"}

    @pytest.mark.parametrize("path", ["../j4ne-evil/secret.txt", "..\\j4ne-evil\\secret.txt", "../../etc/passwd"])
    def test_sibling_and_parent_paths_are_outside(self, layout, path):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert "outside" in run(fs, "filesystem.read-file", path=path)["error"]

    def test_absolute_path_outside_root(self, layout):
        root, sibling = layout
        fs = FilesystemToolProvider(str(root))
        result = run(fs, "filesystem.read-file", path=str(sibling / "secret.txt"))
        assert "outside" in result["error"]

    def test_write_to_sibling_is_refused(self, layout):
        root, sibling = layout
        fs = FilesystemToolProvider(str(root))
        result = run(fs, "filesystem.write-file", path="../j4ne-evil/written.txt", content="x", create_dirs=False)
        assert "outside" in result["error"]
        assert not (sibling / "written.txt").exists()

    def test_symlink_out_of_root_is_outside(self, layout):
        root, sibling = layout
        try:
            os.symlink(sibling, root / "link", target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("cannot create symlinks here")
        fs = FilesystemToolProvider(str(root))
        assert "outside" in run(fs, "filesystem.read-file", path="link/secret.txt")["error"]

    def test_listing_a_sibling_is_refused(self, layout):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert "outside" in run(fs, "filesystem.list-files", directory="../j4ne-evil")["error"]


class TestFilesystemProtectedPaths:
    @pytest.mark.parametrize("path", [".", "", "./", "notes/.."])
    def test_root_cannot_be_deleted(self, layout, path):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        result = run(fs, "filesystem.delete-file", path=path, recursive=True)
        assert "error" in result
        assert (root / "notes.txt").exists() and (root / ".git").exists()

    def test_git_directory_cannot_be_deleted(self, layout):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert "error" in run(fs, "filesystem.delete-file", path=".git", recursive=True)
        assert (root / ".git" / "config").exists()

    @pytest.mark.parametrize("path", [".env", ".git/config", ".git/hooks/pre-commit"])
    def test_protected_files_cannot_be_written(self, layout, path):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        result = run(fs, "filesystem.write-file", path=path, content="pwned", create_dirs=True)
        assert "ignored" in result["error"]
        assert (root / ".env").read_text(encoding="utf-8") == "API_KEY=secret"

    def test_protected_even_when_gitignore_omits_them(self, layout):
        # A .gitignore replaces the default patterns; .git and .env must stay protected
        root, _ = layout
        (root / ".gitignore").write_text("*.log\n", encoding="utf-8")
        fs = FilesystemToolProvider(str(root))
        assert "ignored" in run(fs, "filesystem.read-file", path=".env")["error"]
        assert "ignored" in run(fs, "filesystem.read-file", path=".git/config")["error"]

    @pytest.mark.skipif(os.name != "nt", reason="Windows file names")
    @pytest.mark.parametrize("path", [".ENV", ".env::$DATA", ".env:stream"])
    def test_windows_spellings_of_env(self, layout, path):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert "error" in run(fs, "filesystem.read-file", path=path)

    def test_ordinary_write_and_delete_still_work(self, layout):
        root, _ = layout
        fs = FilesystemToolProvider(str(root))
        assert run(fs, "filesystem.write-file", path="sub/new.txt", content="x", create_dirs=True)["success"]
        assert run(fs, "filesystem.delete-file", path="sub", recursive=True)["success"]
        assert not (root / "sub").exists()

    def test_large_files_are_truncated(self, layout):
        root, _ = layout
        (root / "big.txt").write_text("x" * 150_000, encoding="utf-8")
        fs = FilesystemToolProvider(str(root))
        result = run(fs, "filesystem.read-file", path="big.txt")
        assert result["truncated"] is True
        assert len(result["content"]) == 100_000


@pytest.fixture
def repo(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    root = tmp_path / "repo"
    root.mkdir()
    git = lambda *args: subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "test")
    (root / "f.txt").write_text("a\n", encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "init")
    (root / "f.txt").write_text("a\nb\n", encoding="utf-8")
    return root


class TestGit:
    def test_paths_resolve_against_root_not_cwd(self, repo, tmp_path, monkeypatch):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        provider = GitToolProvider(str(repo))
        result = run(provider, "git.status", repository_path=".")
        assert result["success"], result
        assert result["files"][0]["file"] == "f.txt"

    def test_repository_outside_root_is_refused(self, repo):
        provider = GitToolProvider(str(repo / "nested-root"))
        assert "outside" in run(provider, "git.status", repository_path="..")["error"]

    def test_diff_option_injection_writes_nothing(self, repo, tmp_path):
        provider = GitToolProvider(str(repo))
        target = tmp_path / "outside.txt"
        run(provider, "git.diff", repository_path=".", file_path=f"--output={target}")
        assert not target.exists()

    def test_diff_of_a_file(self, repo):
        provider = GitToolProvider(str(repo))
        result = run(provider, "git.diff", repository_path=".", file_path="f.txt")
        assert result["has_changes"] and "+b" in result["diff"]

    def test_add_takes_option_lookalikes_as_paths(self, repo):
        provider = GitToolProvider(str(repo))
        result = run(provider, "git.add", repository_path=".", files="--chmod=+x f.txt")
        # '--chmod=+x' is now a pathspec that matches nothing, so git refuses it
        assert "error" in result

    @pytest.mark.parametrize("name", ["-D", "--orphan"])
    def test_branch_names_that_are_options(self, repo, name):
        provider = GitToolProvider(str(repo))
        result = run(provider, "git.branch", repository_path=".", action="create", branch_name=name)
        assert "Invalid branch name" in result["error"]

    def test_switch_does_not_discard_a_files_changes(self, repo):
        # 'git checkout f.txt' would have thrown away the edit to f.txt
        provider = GitToolProvider(str(repo))
        assert "error" in run(provider, "git.branch", repository_path=".", action="switch", branch_name="f.txt")
        assert (repo / "f.txt").read_text(encoding="utf-8") == "a\nb\n"


class TestSQLite:
    @pytest.fixture
    def provider(self, tmp_path):
        provider = SQLiteToolProvider(str(tmp_path / "tools.db"))
        run(provider, "sqlite.create-table", query="CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
        run(provider, "sqlite.write-query", query="INSERT INTO t (name) VALUES ('a'), ('b')")
        yield provider
        provider._conn.close()

    def test_uses_its_own_database(self, provider, tmp_path):
        with sqlite3.connect(tmp_path / "tools.db") as conn:
            assert conn.execute("SELECT count(*) FROM t").fetchone()[0] == 2

    def test_read_query_reads(self, provider):
        result = run(provider, "sqlite.read-query", query="SELECT name FROM t ORDER BY id")
        assert result["results"] == [{"name": "a"}, {"name": "b"}]

    @pytest.mark.parametrize("query", [
        "WITH x AS (SELECT 1) DELETE FROM t",
        "WITH x AS (SELECT 1) INSERT INTO t (name) SELECT 'c' FROM x",
    ])
    def test_read_query_cannot_write(self, provider, query):
        assert "error" in run(provider, "sqlite.read-query", query=query)
        assert len(run(provider, "sqlite.read-query", query="SELECT * FROM t")["results"]) == 2

    def test_attach_is_denied(self, provider, tmp_path):
        other = tmp_path / "other.db"
        result = run(provider, "sqlite.write-query", query=f"ATTACH DATABASE '{other}' AS other")
        assert "error" in result
        assert not other.exists()

    def test_vacuum_into_is_denied(self, provider, tmp_path):
        copy = tmp_path / "copy.db"
        assert "error" in run(provider, "sqlite.write-query", query=f"VACUUM INTO '{copy}'")
        assert not copy.exists()

    def test_describe_table_takes_a_name_not_sql(self, provider):
        assert run(provider, "sqlite.describe-table", table_name="t")["schema"][0]["name"] == "id"
        assert run(provider, "sqlite.describe-table", table_name="t); DROP TABLE t; --")["schema"] == []
        assert len(run(provider, "sqlite.read-query", query="SELECT * FROM t")["results"]) == 2


class TestGitHubUrls:
    def test_names_and_paths_are_encoded(self):
        url = repo_url("https://api.github.com", "octo", "repo.js", "contents", "docs/a b#c.md")
        assert url == "https://api.github.com/repos/octo/repo.js/contents/docs/a%20b%23c.md"

    @pytest.mark.parametrize("owner,repo,path", [
        ("x", "y", "../../../../user"),
        ("x", "y", "docs/../../../user"),
        ("..", "y", "README.md"),
        ("x/../..", "y", "README.md"),
        ("x", "y?q=1", "README.md"),
    ])
    def test_dot_segments_and_odd_names_are_refused(self, owner, repo, path):
        with pytest.raises(ValueError):
            repo_url("https://api.github.com", owner, repo, "contents", path)
