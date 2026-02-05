"""Utility helpers for content automation."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

META_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 5,
            "maxItems": 5,
        },
        "description": {"type": "string", "minLength": 155, "maxLength": 160},
        "platform": {"type": "string"},
        "date": {"type": "string"},
        "slug": {"type": "string"},
    },
    "required": ["title", "keywords", "description", "platform", "date", "slug"],
    "additionalProperties": False,
}


def slugify(text: str) -> str:
    """Convert text into a filesystem-friendly slug."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    slug = re.sub(r"[\s-]+", "-", cleaned)
    return slug or "untitled"


def get_output_dir(
    base_dir: str | Path,
    topic: Optional[str] = None,
    date_value: Optional[date] = None,
) -> Path:
    """Return the output directory for a given date and optional topic."""
    if date_value is None:
        date_value = date.today()
    date_folder = date_value.isoformat()
    base_path = Path(base_dir) / date_folder
    if topic:
        return base_path / slugify(topic)
    return base_path


def ensure_dir(path: Path) -> None:
    """Create a directory if it does not exist."""
    path.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    """Write text content to a file."""
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON payload to disk."""
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
