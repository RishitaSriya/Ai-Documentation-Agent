"""Structured logging configuration for AI API Doc Agent."""

import logging
import sys
from typing import Any, Optional


class PipelineFormatter(logging.Formatter):
    """Custom formatter for structured pipeline and API logging."""

    def format(self, record: logging.LogRecord) -> str:
        # Check if record has extra attributes
        stage = getattr(record, "stage", None)
        repo = getattr(record, "repo", None)
        commit = getattr(record, "commit", None)

        prefix_parts = []
        if stage:
            prefix_parts.append(f"[{stage.upper()}]")
        if repo:
            prefix_parts.append(f"repo={repo}")
        if commit:
            prefix_parts.append(f"commit={commit[:7] if len(commit) >= 7 else commit}")

        prefix = " ".join(prefix_parts)
        if prefix:
            record.msg = f"{prefix} {record.msg}"

        return super().format(record)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup structured application logger."""
    logger = logging.getLogger("api_agent")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = PipelineFormatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = setup_logging()


def log_pipeline_event(
    stage: str,
    message: str,
    repo: Optional[str] = None,
    commit: Optional[str] = None,
    level: int = logging.INFO,
    **extra: Any,
) -> None:
    """Helper to log structured pipeline events with context."""
    extra_dict = {"stage": stage, "repo": repo, "commit": commit}
    extra_dict.update(extra)
    logger.log(level, message, extra=extra_dict)
