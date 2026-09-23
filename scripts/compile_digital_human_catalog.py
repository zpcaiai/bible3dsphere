#!/usr/bin/env python3
"""Compile the reviewed skills-package metadata into a backend runtime artifact.

This is intentionally one-way: production never imports files from the sibling
frontend checkout.  Re-run this compiler when adopting a new package version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml


def _read_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _verify_manifest(package: Path) -> str:
    manifest = package / "MANIFEST.sha256"
    seen: set[str] = set()
    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            expected, relative = line.split(maxsplit=1)
        except ValueError as exc:
            raise ValueError(f"invalid manifest line {line_number}") from exc
        relative = relative[2:] if relative.startswith("./") else relative
        if relative in seen:
            raise ValueError(f"duplicate manifest path: {relative}")
        seen.add(relative)
        path = (package / relative).resolve()
        if not path.is_relative_to(package) or not path.is_file():
            raise ValueError(f"unsafe or missing manifest path: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"manifest digest mismatch: {relative}")
    if not seen:
        raise ValueError("package manifest is empty")
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def compile_catalog(package: Path) -> dict:
    source_manifest_sha256 = _verify_manifest(package)
    skill = _read_yaml(package / "skill.yaml")
    if skill.get("version") != "1.3.0":
        raise ValueError(f"expected package 1.3.0, got {skill.get('version')!r}")
    index = _read_yaml(package / "examples" / "characters.index.yaml")
    aliases = _read_yaml(package / "examples" / "identity-aliases.yaml")
    expected_count = int(skill["character_pack"]["count"])
    if len(index.get("characters", [])) != expected_count:
        raise ValueError("character count does not match skill.yaml")

    compiled = []
    for indexed in index["characters"]:
        character_id = indexed["id"]
        base = package / "examples" / character_id
        character = _read_yaml(base / "character.yaml")
        questions = _read_yaml(base / "recommended-questions.yaml")
        truth_set = _read_yaml(base / "truth-set.yaml")
        relationships = _read_yaml(base / "relationships.yaml")
        persona_path = base / "persona.system.md"
        persona_text = persona_path.read_text(encoding="utf-8").strip()
        if character.get("id") != character_id or truth_set.get("characterId") != character_id:
            raise ValueError(f"identity mismatch for {character_id}")
        if relationships.get("characterId") != character_id:
            raise ValueError(f"relationship identity mismatch for {character_id}")
        compiled.append(
            {
                "id": character_id,
                "canonicalName": character["canonicalName"],
                "englishName": character.get("englishName") or character_id,
                "period": character.get("period"),
                "catalogStatus": indexed["status"],
                "catalogTier": "deep-alpha" if len(compiled) < 24 else "standard-alpha",
                "recommendedQuestions": [item["text"] for item in questions.get("questions", [])],
                "ragScope": character.get("persona", {}).get("ragScope", []),
                "persona": {
                    "text": persona_text,
                    "sha256": hashlib.sha256(persona_text.encode("utf-8")).hexdigest(),
                },
                "relationships": relationships.get("relationships", []),
                "truthCaseCount": len(truth_set.get("cases", [])),
                "truthCaseIds": [item["id"] for item in truth_set.get("cases", [])],
                "truthCases": truth_set.get("cases", []),
            }
        )

    return {
        "version": skill["version"],
        "sourceManifestSha256": source_manifest_sha256,
        "characterCount": len(compiled),
        "truthCaseCount": sum(item["truthCaseCount"] for item in compiled),
        "characters": compiled,
        "identity": {
            "policy": aliases.get("policy", {}),
            "ambiguous": aliases.get("ambiguous", []),
            "stableLabels": aliases.get("stableLabels", {}),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, default=Path("backend/digital_human/catalog.v1.3.0.json"))
    args = parser.parse_args()
    payload = compile_catalog(args.package.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"compiled {payload['characterCount']} characters / {payload['truthCaseCount']} truth cases -> {args.output}")


if __name__ == "__main__":
    main()
