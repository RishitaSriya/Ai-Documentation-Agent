"""Change detector coordinating Git diff and API comparison."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import logger, log_pipeline_event
from app.services.analyzers.fastapi_analyzer import FastAPIAnalyzer
from app.services.git_service import GitService
from app.services.openapi.comparator import APIComparator, DetectedAPIChange


class ChangeDetector:
    """Detects Git-level source changes and translates them to structural API changes."""

    def __init__(self, analyzer: Optional[FastAPIAnalyzer] = None):
        self.analyzer = analyzer or FastAPIAnalyzer()

    def detect_changes(
        self,
        repository_path: Path | str,
        before_sha: Optional[str],
        after_sha: str
    ) -> Dict[str, Any]:
        """Inspect Git diff and compute detected structural API changes."""
        repo_p = Path(repository_path).resolve()
        log_pipeline_event("CHANGE_DETECTOR", f"Checking Git diff {before_sha[:7] if before_sha else 'initial'} -> {after_sha[:7]}")

        # 1. Get changed files from Git
        git_diff_result = GitService.get_diff_between_commits(repo_p, before_sha, after_sha)
        all_changed_files = git_diff_result["changed_files"]

        # 2. Filter for Python source files
        python_changed_files = [
            f["file_path"] for f in all_changed_files
            if f["file_path"].endswith(".py")
        ]

        logger.info(f"Found {len(all_changed_files)} total changed files ({len(python_changed_files)} Python files).")

        # 3. Analyze Current API snapshot
        curr_snapshot = self.analyzer.analyze(repo_p, commit_sha=after_sha)

        # 4. Analyze Previous API snapshot (if before_sha exists)
        prev_snapshot = None
        if before_sha and before_sha != "0000000000000000000000000000000000000000":
            try:
                prev_snapshot = self.analyzer.analyze(repo_p, commit_sha=before_sha)
            except Exception as e:
                logger.warning(f"Failed to analyze previous commit {before_sha}: {str(e)}")

        # 5. Deterministically compare snapshots
        api_changes = APIComparator.compare(prev_snapshot, curr_snapshot)

        return {
            "has_python_changes": len(python_changed_files) > 0 or before_sha is None,
            "has_api_changes": len(api_changes) > 0,
            "changed_files": all_changed_files,
            "python_changed_files": python_changed_files,
            "git_diff_text": git_diff_result["diff_text"],
            "prev_snapshot": prev_snapshot,
            "curr_snapshot": curr_snapshot,
            "api_changes": api_changes,
        }
