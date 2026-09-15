"""Tests for GitService using real local Git repositories."""

import os
from pathlib import Path
import pytest
from git import Repo

from app.services.git_service import GitService


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary initialized Git repository with sample commits."""
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # Configure user for commits in test
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Commit 1: Initial files
    (repo_dir / "app").mkdir()
    main_file = repo_dir / "app" / "main.py"
    main_file.write_text("print('hello world')\n", encoding="utf-8")

    readme_file = repo_dir / "README.md"
    readme_file.write_text("# Sample API\n", encoding="utf-8")

    repo.index.add(["app/main.py", "README.md"])
    commit1 = repo.index.commit("Initial commit")

    # Commit 2: Add routes and modify main.py
    (repo_dir / "app" / "routes").mkdir()
    users_route = repo_dir / "app" / "routes" / "users.py"
    users_route.write_text("@router.get('/users')\ndef get_users(): pass\n", encoding="utf-8")

    main_file.write_text("print('hello updated')\n", encoding="utf-8")
    repo.index.add(["app/routes/users.py", "app/main.py"])
    commit2 = repo.index.commit("Add users route and update main")

    return {
        "path": repo_dir,
        "repo": repo,
        "commit1": commit1.hexsha,
        "commit2": commit2.hexsha,
    }


def test_is_git_repo(temp_git_repo, tmp_path):
    """Test Git repository detection."""
    assert GitService.is_git_repo(temp_git_repo["path"]) is True
    assert GitService.is_git_repo(tmp_path / "non_existent") is False


def test_get_commit_info(temp_git_repo):
    """Test extracting commit info."""
    info = GitService.get_commit_info(temp_git_repo["path"], temp_git_repo["commit2"])
    assert info["sha"] == temp_git_repo["commit2"]
    assert info["parent_sha"] == temp_git_repo["commit1"]
    assert info["message"] == "Add users route and update main"
    assert "Test User" in info["author"]
    assert info["timestamp"] is not None


def test_get_diff_between_commits(temp_git_repo):
    """Test diff computation between two commits."""
    diff_result = GitService.get_diff_between_commits(
        temp_git_repo["path"],
        temp_git_repo["commit1"],
        temp_git_repo["commit2"]
    )

    assert diff_result["before_sha"] == temp_git_repo["commit1"]
    assert diff_result["after_sha"] == temp_git_repo["commit2"]
    changed_files = diff_result["changed_files"]
    assert len(changed_files) == 2

    file_paths = {f["file_path"]: f["change_type"] for f in changed_files}
    assert file_paths.get("app/routes/users.py") == "added"
    assert file_paths.get("app/main.py") == "modified"


def test_read_file_at_commit(temp_git_repo):
    """Test reading file content across commits and filesystem."""
    # Read from commit 1
    content_c1 = GitService.read_file_at_commit(
        temp_git_repo["path"], "app/main.py", temp_git_repo["commit1"]
    )
    assert content_c1 is not None
    assert content_c1.strip() == "print('hello world')"

    # Read from commit 2
    content_c2 = GitService.read_file_at_commit(
        temp_git_repo["path"], "app/main.py", temp_git_repo["commit2"]
    )
    assert content_c2 is not None
    assert content_c2.strip() == "print('hello updated')"

    # Read directly from filesystem
    content_fs = GitService.read_file_at_commit(temp_git_repo["path"], "app/main.py")
    assert content_fs is not None
    assert content_fs.strip() == "print('hello updated')"


def test_list_python_files(temp_git_repo):
    """Test scanning python files in repository."""
    py_files = GitService.list_python_files(temp_git_repo["path"])
    assert "app/main.py" in py_files
    assert "app/routes/users.py" in py_files
    assert "README.md" not in py_files
