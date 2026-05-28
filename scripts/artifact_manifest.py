#!/usr/bin/env python3
"""Create a reproducibility manifest for generated retrieval artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACTS = [
    "bible_cuv.index",
    "bible_cuv_embeddings.npy",
    "bible_cuv_metadata.pkl",
    "bible_cuv_config.json",
    "bible_bilingual_config.json",
    "emotion_features_map.json",
    "emotion_exemplar_verse_matches.json",
    "emotion_sphere_layout.json",
    "emotion_sphere_layout.csv",
]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_if_present(path: Path) -> Any:
    if not path.exists() or path.suffix.lower() != ".json":
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def artifact_record(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    record: dict[str, Any] = {
        "path": str(path.relative_to(root) if path.is_relative_to(root) else path),
        "bytes": stat.st_size,
        "sha256": sha256_file(path),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
    }
    config = load_json_if_present(path)
    if isinstance(config, dict):
        for key in (
            "embedding_model",
            "vector_dimension",
            "vector_count",
            "metric",
            "normalization",
            "source_csv",
            "input_template",
        ):
            if key in config:
                record[key] = config[key]
    return record


def build_manifest(paths: list[Path], root: Path) -> dict[str, Any]:
    existing = [path for path in paths if path.exists()]
    missing = [str(path.relative_to(root) if path.is_relative_to(root) else path) for path in paths if not path.exists()]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(existing),
        "artifacts": [artifact_record(path, root) for path in existing],
        "missing": missing,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("artifact_manifest.json"))
    parser.add_argument("--artifacts", nargs="*", default=DEFAULT_ARTIFACTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    paths = [(root / artifact).resolve() for artifact in args.artifacts]
    manifest = build_manifest(paths, root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "artifact_count": manifest["artifact_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
