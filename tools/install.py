#!/usr/bin/env python3
"""Safely install this Skill into a Codex project without overwriting files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
MARKER = "INSTALL.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest() -> dict:
    manifest = json.loads((ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("name") != "music-education-prose":
        raise ValueError("Unexpected Skill name in MANIFEST.json")
    for relative, expected in manifest.get("files", {}).items():
        rel = PurePosixPath(relative)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"Unsafe manifest path: {relative}")
        source = ROOT.joinpath(*rel.parts)
        if source.is_symlink() or not source.is_file() or digest(source) != expected:
            raise ValueError(f"Package integrity check failed: {relative}")
    return manifest


def project_files_match(target: Path, manifest: dict) -> bool:
    marker_path = target / MARKER
    if not marker_path.is_file():
        return False
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = {name: manifest["files"][name] for name in manifest["install_files"]}
    if marker.get("name") != manifest["name"] or marker.get("files") != expected:
        return False
    actual_names = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.name != MARKER
    }
    if actual_names != set(expected):
        return False
    return all(digest(target / name) == sha for name, sha in expected.items())


def install(project: Path, dry_run: bool = False) -> Path:
    project = project.expanduser().resolve(strict=True)
    if not project.is_dir():
        raise ValueError(f"Project root is not a directory: {project}")
    manifest = load_manifest()
    skills_parent = project / ".agents" / "skills"
    target = skills_parent / manifest["name"]
    for path in (project / ".agents", skills_parent, target):
        if path.is_symlink():
            raise ValueError(f"Refusing to write through symlink: {path}")
    if target.exists():
        if project_files_match(target, manifest):
            print(f"Already installed and verified: {target}")
            return target
        raise FileExistsError(f"Target exists and will not be overwritten: {target}")
    if dry_run:
        print(f"Would install {manifest['name']} {manifest['version']} to {target}")
        return target

    skills_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{manifest['name']}.stage-", dir=skills_parent))
    try:
        expected: dict[str, str] = {}
        for relative in manifest["install_files"]:
            rel = PurePosixPath(relative)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"Unsafe install path: {relative}")
            source = ROOT.joinpath(*rel.parts)
            destination = stage.joinpath(*rel.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            expected[relative] = manifest["files"][relative]
        marker = {
            "name": manifest["name"],
            "version": manifest["version"],
            "files": expected,
        }
        (stage / MARKER).write_text(json.dumps(marker, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(stage, target)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise
    print(f"Installed {manifest['name']} {manifest['version']} to {target}")
    return target


def verify(project: Path) -> Path:
    project = project.expanduser().resolve(strict=True)
    manifest = load_manifest()
    target = project / ".agents" / "skills" / manifest["name"]
    if not project_files_match(target, manifest):
        raise ValueError(f"Installed Skill is missing, modified, or out of date: {target}")
    print(f"Verified installation: {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Existing Codex project root")
    parser.add_argument("--verify", action="store_true", help="Verify an existing installation")
    parser.add_argument("--dry-run", action="store_true", help="Show the destination without writing")
    args = parser.parse_args()
    project = Path(args.project)
    if args.verify:
        verify(project)
    else:
        install(project, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
