#!/usr/bin/env python3
"""Validate release asset metadata and optionally verify remote bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.digital_human.assets import load_manifest_file, validated_characters
from backend.digital_human.registry import catalog_artifact


def remote_sha256(url: str, max_bytes: int) -> str:
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(url, headers={"User-Agent": "SpiritualPlanetAssetVerifier/1.3"})
    with urllib.request.urlopen(request, timeout=30) as response:
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                raise ValueError(f"asset exceeds {max_bytes} bytes")
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--verify-bytes", action="store_true")
    parser.add_argument("--max-asset-mb", type=int, default=200)
    parser.add_argument("--require-core-100", action="store_true")
    args = parser.parse_args()
    manifest = load_manifest_file(args.manifest)
    valid = validated_characters(manifest)
    declared = manifest.get("characters") if isinstance(manifest.get("characters"), dict) else {}
    failures = [character_id for character_id in declared if character_id not in valid]
    expected = {item["id"] for item in catalog_artifact()["characters"]}
    if args.require_core_100:
        failures.extend(sorted(expected - set(valid)))
    byte_checks = []
    if args.verify_bytes:
        for character_id, asset in valid.items():
            for kind, url_key, hash_key in (("model", "modelUrl", "modelSha256"), ("portrait", "portraitUrl", "portraitSha256")):
                observed = remote_sha256(asset[url_key], args.max_asset_mb * 1024 * 1024)
                matched = observed == asset[hash_key]
                byte_checks.append({"characterId": character_id, "kind": kind, "matched": matched})
                if not matched:
                    failures.append(f"{character_id}:{kind}:sha256")
    failures = sorted(set(failures))
    result = {"schemaVersion": "digital-human-asset-validation/v1", "declared": len(declared), "valid": len(valid), "remoteByteChecks": byte_checks, "failures": failures, "result": "PASS" if not failures else "FAIL"}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
