"""File and directory utility helpers."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


def ensure_dir(path: Path | str) -> Path:
    """Ensure directory exists and return Path object."""
    p = Path(path).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json_file(file_path: Path | str) -> Optional[Dict[str, Any]]:
    """Safely read JSON file."""
    p = Path(file_path)
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json_file(file_path: Path | str, data: Any, indent: int = 2) -> None:
    """Write data to a JSON file cleanly."""
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, default=str)


def read_yaml_file(file_path: Path | str) -> Optional[Dict[str, Any]]:
    """Safely read YAML file."""
    p = Path(file_path)
    if not p.is_file():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def clean_directory(path: Path | str) -> None:
    """Delete all contents inside a directory without removing the directory itself."""
    p = Path(path)
    if p.exists() and p.is_dir():
        for item in p.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
