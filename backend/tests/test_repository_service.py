"""Tests for RepositoryService orchestration."""

import pytest
from pathlib import Path
from git import Repo

from app.schemas.repository import RepositoryCreate
from app.services.repository_service import RepositoryService
from app.core.config import settings


@pytest.mark.asyncio
async def test_connect_and_sync_local_repo(db_session, tmp_path, monkeypatch):
    """Test connecting a local git repository, cloning, and syncing new commits."""
    # Create mock remote repository
    remote_dir = tmp_path / "remote_repo"
    remote_dir.mkdir()
    remote_repo = Repo.init(remote_dir)
    remote_repo.config_writer().set_value("user", "name", "Dev").release()
    remote_repo.config_writer().set_value("user", "email", "dev@example.com").release()

    f1 = remote_dir / "main.py"
    f1.write_text("print('initial')", encoding="utf-8")
    remote_repo.index.add(["main.py"])
    commit1 = remote_repo.index.commit("First commit")

    # Set storage dir to tmp_path
    monkeypatch.setattr(settings, "STORAGE_PATH", str(tmp_path / "storage"))

    # Connect repository
    repo_in = RepositoryCreate(
        owner="test-owner",
        name="test-api",
        clone_url=str(remote_dir),
        default_branch="master" if "master" in [h.name for h in remote_repo.heads] else "main",
    )

    db_repo = await RepositoryService.connect_repository(db_session, repo_in)
    assert db_repo.id is not None
    assert db_repo.owner == "test-owner"
    assert db_repo.name == "test-api"
    assert db_repo.last_processed_commit == commit1.hexsha
    assert len(db_repo.commits) == 1

    # Add second commit to remote repo
    f2 = remote_dir / "users.py"
    f2.write_text("print('users')", encoding="utf-8")
    remote_repo.index.add(["users.py"])
    commit2 = remote_repo.index.commit("Second commit")

    # Sync repository
    synced_repo = await RepositoryService.sync_repository(db_session, db_repo.id)
    assert synced_repo.last_processed_commit == commit2.hexsha
    assert len(synced_repo.commits) == 2
