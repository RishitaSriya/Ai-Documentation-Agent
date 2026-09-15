"""Git operations service using GitPython."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import git
from git import Repo, GitCommandError

from app.core.logging import logger, log_pipeline_event

# Ensure Git never hangs waiting for interactive terminal credentials
os.environ["GIT_TERMINAL_PROMPT"] = "0"
os.environ["GIT_ASKPASS"] = "echo"


class GitChangeItem:
    """Represents a single changed file in a Git diff."""
    def __init__(self, file_path: str, change_type: str, old_path: Optional[str] = None, new_path: Optional[str] = None):
        self.file_path = file_path
        self.change_type = change_type  # A: added, M: modified, D: deleted, R: renamed
        self.old_path = old_path
        self.new_path = new_path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "old_path": self.old_path,
            "new_path": self.new_path,
        }


class GitService:
    """Service for local and remote Git repository operations."""

    @staticmethod
    def is_git_repo(path: Path | str) -> bool:
        """Check if path is a valid Git repository."""
        try:
            Repo(path)
            return True
        except Exception:
            return False

    @staticmethod
    def get_repo(path: Path | str) -> Repo:
        """Get or initialize a Repo instance."""
        return Repo(path)

    @classmethod
    def clone_repository(
        cls,
        clone_url: str,
        target_path: Path | str,
        branch: Optional[str] = "main",
        token: Optional[str] = None,
        depth: int = 1
    ) -> Repo:
        """Clone a Git repository into target_path in non-interactive mode."""
        target_p = Path(target_path).resolve()
        target_p.parent.mkdir(parents=True, exist_ok=True)

        auth_url = clone_url
        if token and clone_url.startswith("https://"):
            # Inject token for authentication: https://token@github.com/...
            auth_url = clone_url.replace("https://", f"https://x-access-token:{token}@")

        logger.info(f"Cloning repository {clone_url} to {target_p} (branch: {branch}, depth: {depth})...")
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "echo",
        }
        try:
            # Try shallow clone first for speed
            kwargs = {"env": env}
            if branch:
                kwargs["branch"] = branch
            if depth > 0 and not str(clone_url).startswith("/") and not (Path(clone_url).exists() if len(str(clone_url)) < 260 else False):
                kwargs["depth"] = depth

            repo = Repo.clone_from(auth_url, str(target_p), **kwargs)
            return repo
        except Exception as e:
            logger.warning(f"Shallow clone attempt failed ({str(e)}). Retrying full clone...")
            try:
                if branch:
                    repo = Repo.clone_from(auth_url, str(target_p), branch=branch, env=env)
                else:
                    repo = Repo.clone_from(auth_url, str(target_p), env=env)
                return repo
            except GitCommandError as gce:
                logger.error(f"Failed to clone repository {clone_url}: {gce.stderr}")
                raise RuntimeError(f"Git clone failed: {gce.stderr or str(gce)}")

    @classmethod
    def fetch_and_pull(cls, repo_path: Path | str, branch: str = "main") -> str:
        """Pull latest changes from remote and return current HEAD commit SHA."""
        repo = cls.get_repo(repo_path)
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "echo",
        }
        try:
            with repo.git.custom_environment(**env):
                origin = repo.remotes.origin
                origin.fetch()
                try:
                    repo.git.checkout(branch)
                except Exception:
                    pass
                origin.pull()
                head_sha = repo.head.commit.hexsha
                logger.info(f"Pulled latest changes for {repo_path}. HEAD is at {head_sha[:7]}")
                return head_sha
        except Exception as e:
            logger.error(f"Git pull failed on {repo_path}: {str(e)}")
            raise RuntimeError(f"Git pull failed: {str(e)}")

    @classmethod
    def get_commit_info(cls, repo_path: Path | str, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        """Extract metadata for a specific commit or HEAD."""
        repo = cls.get_repo(repo_path)
        commit = repo.commit(commit_sha) if commit_sha else repo.head.commit

        parent_sha = commit.parents[0].hexsha if commit.parents else None
        committed_dt = datetime.fromtimestamp(commit.committed_date, tz=timezone.utc)

        return {
            "sha": commit.hexsha,
            "parent_sha": parent_sha,
            "message": commit.message.strip() if commit.message else "",
            "author": f"{commit.author.name} <{commit.author.email}>",
            "timestamp": committed_dt,
        }

    @classmethod
    def get_diff_between_commits(
        cls,
        repo_path: Path | str,
        before_sha: Optional[str],
        after_sha: str
    ) -> Dict[str, Any]:
        """Compute git diff and list of changed files between two commits."""
        repo = cls.get_repo(repo_path)
        after_commit = repo.commit(after_sha)

        if not before_sha or before_sha == "0000000000000000000000000000000000000000":
            if after_commit.parents:
                before_commit = after_commit.parents[0]
            else:
                before_commit = None
        else:
            try:
                before_commit = repo.commit(before_sha)
            except Exception:
                before_commit = after_commit.parents[0] if after_commit.parents else None

        changed_files: List[Dict[str, Any]] = []
        diff_text = ""

        if before_commit:
            diff_index = before_commit.diff(after_commit)
            try:
                diff_text = repo.git.diff(before_commit.hexsha, after_commit.hexsha)
            except Exception:
                diff_text = ""

            for d in diff_index:
                if d.new_file:
                    change_type = "added"
                    file_path = d.b_path
                elif d.deleted_file:
                    change_type = "deleted"
                    file_path = d.a_path
                elif d.renamed_file:
                    change_type = "renamed"
                    file_path = d.b_path
                else:
                    change_type = "modified"
                    file_path = d.b_path or d.a_path

                changed_files.append({
                    "file_path": file_path,
                    "change_type": change_type,
                    "old_path": d.a_path,
                    "new_path": d.b_path,
                })
        else:
            for item in after_commit.tree.traverse():
                if item.type == "blob":
                    changed_files.append({
                        "file_path": item.path,
                        "change_type": "added",
                        "old_path": None,
                        "new_path": item.path,
                    })
            try:
                diff_text = repo.git.show(after_commit.hexsha)
            except Exception:
                diff_text = ""

        return {
            "before_sha": before_commit.hexsha if before_commit else None,
            "after_sha": after_commit.hexsha,
            "changed_files": changed_files,
            "diff_text": diff_text,
        }

    @classmethod
    def read_file_at_commit(
        cls,
        repo_path: Path | str,
        file_path: str,
        commit_sha: Optional[str] = None
    ) -> Optional[str]:
        """Read content of a file at a specific commit or on filesystem."""
        p = Path(repo_path)
        if commit_sha is None:
            target = p / file_path
            if target.is_file():
                try:
                    return target.read_text(encoding="utf-8")
                except Exception:
                    return None
            return None

        try:
            repo = cls.get_repo(repo_path)
            commit = repo.commit(commit_sha)
            blob = commit.tree / file_path
            return blob.data_stream.read().decode("utf-8")
        except Exception:
            return None

    @classmethod
    def list_python_files(cls, repo_path: Path | str, subdir: str = "") -> List[str]:
        """List all .py files in repository or subdirectory."""
        base = Path(repo_path)
        target = base / subdir if subdir else base
        if not target.exists():
            return []

        py_files = []
        for root, dirs, files in os.walk(target):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv", "env")]
            for f in files:
                if f.endswith(".py"):
                    full = Path(root) / f
                    rel = full.relative_to(base)
                    py_files.append(str(rel).replace("\\", "/"))

        return sorted(py_files)
