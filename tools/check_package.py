#!/usr/bin/env python3
"""Validate package structure, links, evaluation cases, and manifest hashes."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PATH_PATTERN = re.compile(r"/(?:Users|home)/[^/\s]+/(?:Downloads|Desktop)/")


def fail(message: str) -> None:
    raise ValueError(message)


def safe_package_file(root: Path, relative: str) -> Path:
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts:
        fail(f"Unsafe path in manifest: {relative}")
    path = root.joinpath(*rel.parts)
    if path.is_symlink() or not path.is_file():
        fail(f"Missing or non-regular package file: {relative}")
    return path


def parse_frontmatter(text: str) -> tuple[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if not match:
        fail("SKILL.md must start with YAML frontmatter")
    lines = match.group(1).splitlines()
    name_match = next((re.fullmatch(r"name:\s*([a-z0-9-]+)\s*", line) for line in lines if line.startswith("name:")), None)
    if not name_match:
        fail("Frontmatter is missing a valid name")
    desc_lines: list[str] = []
    in_description = False
    for line in lines:
        if line.startswith("description:"):
            in_description = True
            desc_lines.append(line.split(":", 1)[1].strip().strip(">-|'\" "))
            continue
        if in_description and line and not line.startswith(" "):
            break
        if in_description:
            desc_lines.append(line.strip())
    description = " ".join(part for part in desc_lines if part)
    if not description:
        fail("Frontmatter is missing a description")
    return name_match.group(1), description


def check() -> dict:
    manifest_path = ROOT / "MANIFEST.json"
    if not manifest_path.is_file():
        fail("MANIFEST.json is missing; run tools/build_manifest.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        fail("Unsupported manifest schema")
    if manifest.get("version") != (ROOT / "VERSION").read_text(encoding="utf-8").strip():
        fail("VERSION and MANIFEST.json disagree")

    files = manifest.get("files", {})
    if not files:
        fail("Manifest file list is empty")
    for relative, expected in files.items():
        path = safe_package_file(ROOT, relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            fail(f"SHA-256 mismatch: {relative}")

    skill_path = ROOT / "SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8")
    name, description = parse_frontmatter(skill_text)
    if name != manifest.get("name"):
        fail("Skill frontmatter and manifest names disagree")
    if "[TODO" in skill_text:
        fail("Unfinished placeholder remains in SKILL.md")
    for target in re.findall(r"\[[^]]+\]\((references/[^)#]+)\)", skill_text):
        if not (ROOT / target).is_file():
            fail(f"Broken reference link: {target}")

    runtime = set(manifest.get("install_files", []))
    required_runtime = {"SKILL.md", "agents/openai.yaml"}
    if not required_runtime.issubset(runtime):
        fail("Runtime install list must include SKILL.md and agents/openai.yaml")
    if any(path.startswith("references/") and path not in runtime for path in files):
        fail("Every reference must be included in the runtime install list")
    for relative in runtime:
        safe_package_file(ROOT, relative)

    metadata = (ROOT / "agents/openai.yaml").read_text(encoding="utf-8")
    short = re.search(r'^\s*short_description:\s*["\'](.*?)["\']\s*$', metadata, re.M)
    prompt = re.search(r'^\s*default_prompt:\s*["\'](.*?)["\']\s*$', metadata, re.M)
    if not short or not 25 <= len(short.group(1)) <= 64:
        fail("agents/openai.yaml short_description must be 25–64 characters")
    if not prompt or f"${name}" not in prompt.group(1):
        fail("default_prompt must explicitly invoke the Skill")

    cases_doc = json.loads((ROOT / "evals/cases.json").read_text(encoding="utf-8"))
    cases = cases_doc.get("cases", [])
    ids = [case.get("id") for case in cases]
    kinds = {case.get("kind") for case in cases}
    if not cases or len(ids) != len(set(ids)) or None in ids:
        fail("Evaluation case IDs must be present and unique")
    if kinds != {"positive", "negative"}:
        fail("Evaluation set must include positive and negative cases")
    for case in cases:
        for key in ("request", "material", "pass_checks", "fail_signals"):
            if not case.get(key):
                fail(f"Case {case['id']} is missing {key}")

    for relative in files:
        content = safe_package_file(ROOT, relative).read_text(encoding="utf-8", errors="replace")
        if PRIVATE_PATH_PATTERN.search(content):
            fail(f"Private source path or corpus identifier found in {relative}")

    return {"name": name, "description": description, "version": manifest["version"], "file_count": len(files), "case_count": len(cases)}


if __name__ == "__main__":
    try:
        result = check()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
    print("PASS: " + json.dumps(result, ensure_ascii=False))
