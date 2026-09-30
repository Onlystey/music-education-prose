#!/usr/bin/env python3
"""Build a deterministic package manifest for this Skill."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "__pycache__"}


def included_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name == "MANIFEST.json" or path.suffix == ".pyc":
            continue
        relative_parts = path.relative_to(ROOT).parts
        if any(part in EXCLUDED_DIRS or part.startswith(".") for part in relative_parts):
            continue
        paths.append(path)
    return sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    files = included_files()
    runtime = ["SKILL.md", "agents/openai.yaml"]
    runtime.extend(
        path.relative_to(ROOT).as_posix()
        for path in files
        if path.relative_to(ROOT).as_posix().startswith("references/")
    )
    manifest = {
        "schema_version": 1,
        "name": "music-education-prose",
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "entrypoint": "SKILL.md",
        "install_files": runtime,
        "files": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in files
        },
    }
    (ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote MANIFEST.json for {len(files)} files")


if __name__ == "__main__":
    main()
