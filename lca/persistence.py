from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .models import Project


PROJECTS_DIR = Path(__file__).resolve().parents[1] / "projects"


def safe_filename(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in name.strip().lower())
    return "-".join(part for part in cleaned.split("-") if part) or "project"


def project_path(project: Project, directory: Path = PROJECTS_DIR) -> Path:
    return directory / f"{safe_filename(project.name)}-{project.id}.json"


def save_project(project: Project, directory: Path = PROJECTS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = project_path(project, directory)
    path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    return path


def load_project(path: Path) -> Project:
    return Project.from_dict(json.loads(path.read_text(encoding="utf-8")))


def list_project_files(directory: Path = PROJECTS_DIR) -> List[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    return sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
