#!/usr/bin/env python3
"""Unified CLI for BibleSphere retrieval data workflows."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_step(args: list[str], cwd: Path = ROOT_DIR) -> None:
    print(json.dumps({"step": args, "cwd": str(cwd)}, ensure_ascii=False))
    subprocess.run(args, cwd=str(cwd), check=True)


def build_cuv(args: argparse.Namespace) -> None:
    from vectorize_bible_siliconflow import process_bible_vectorization

    process_bible_vectorization(args.csv, output_prefix=args.output_prefix)


def index_cuv(args: argparse.Namespace) -> None:
    run_step([PYTHON, str(ROOT_DIR / "scripts" / "qdrant_bible_index.py")])


def build_bilingual(args: argparse.Namespace) -> None:
    run_step([PYTHON, str(ROOT_DIR / "scripts" / "vectorize_bible_bilingual.py")])


def index_bilingual(args: argparse.Namespace) -> None:
    run_step([PYTHON, str(ROOT_DIR / "scripts" / "qdrant_bible_bilingual.py")])


def build_features(args: argparse.Namespace) -> None:
    run_step([PYTHON, str(ROOT_DIR / "scripts" / "fetch_neuronpedia_emotion_features.py")])


def match_exemplars(args: argparse.Namespace) -> None:
    run_step([PYTHON, str(ROOT_DIR / "scripts" / "batch_search_emotion_exemplars.py")])


def build_layout(args: argparse.Namespace) -> None:
    command = [
        PYTHON,
        str(ROOT_DIR / "scripts" / "build_emotion_sphere_layout.py"),
        "--features-file",
        args.features_file,
        "--cache-file",
        args.cache_file,
        "--output-json",
        args.output_json,
        "--output-csv",
        args.output_csv,
    ]
    run_step(command)


def evaluate(args: argparse.Namespace) -> None:
    command = [
        PYTHON,
        str(ROOT_DIR / "evaluation" / "run_retrieval_eval.py"),
        "--cases",
        args.cases,
        "--output",
        args.output,
        "--top-k",
        str(args.top_k),
        "--backend",
        args.backend,
    ]
    if args.results_file:
        command.extend(["--results-file", args.results_file])
    run_step(command)


def manifest(args: argparse.Namespace) -> None:
    command = [
        PYTHON,
        str(ROOT_DIR / "scripts" / "artifact_manifest.py"),
        "--root",
        str(ROOT_DIR),
        "--output",
        args.manifest_output,
    ]
    command.extend(["--artifacts", *args.artifacts])
    run_step(command)


def full_local(args: argparse.Namespace) -> None:
    build_cuv(args)
    build_layout(args)
    evaluate(args)
    manifest(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    cuv = subparsers.add_parser("build-cuv", help="Build local CUV FAISS vectors")
    cuv.add_argument("--csv", default=str(ROOT_DIR / "bible" / "cuv_bible.csv"))
    cuv.add_argument("--output-prefix", default=str(ROOT_DIR / "bible_cuv"))
    cuv.set_defaults(func=build_cuv)

    subparsers.add_parser("index-cuv", help="Upload CUV vectors to Qdrant").set_defaults(func=index_cuv)

    subparsers.add_parser("build-bilingual", help="Build bilingual vector files").set_defaults(func=build_bilingual)
    subparsers.add_parser("index-bilingual", help="Upload bilingual vectors to Qdrant").set_defaults(func=index_bilingual)
    subparsers.add_parser("build-features", help="Fetch Neuronpedia emotion features").set_defaults(func=build_features)
    subparsers.add_parser("match-exemplars", help="Build feature-to-verse exemplar matches").set_defaults(func=match_exemplars)

    layout = subparsers.add_parser("build-layout", help="Build 3D emotion sphere layout")
    add_layout_args(layout)
    layout.set_defaults(func=build_layout)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate retrieval quality")
    add_eval_args(eval_parser)
    eval_parser.set_defaults(func=evaluate)

    manifest_parser = subparsers.add_parser("manifest", help="Write artifact manifest")
    add_manifest_args(manifest_parser, output_flag="--output")
    manifest_parser.set_defaults(func=manifest)

    full = subparsers.add_parser("full-local", help="Run local build, layout, eval, and manifest")
    full.add_argument("--csv", default=str(ROOT_DIR / "bible" / "cuv_bible.csv"))
    full.add_argument("--output-prefix", default=str(ROOT_DIR / "bible_cuv"))
    add_layout_args(full)
    add_eval_args(full)
    add_manifest_args(full, output_flag="--manifest-output")
    full.set_defaults(func=full_local)

    return parser.parse_args()


def add_layout_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--features-file", default=str(ROOT_DIR / "emotion_features_map.json"))
    parser.add_argument("--cache-file", default=str(ROOT_DIR / "emotion_feature_embedding_cache.json"))
    parser.add_argument("--output-json", default=str(ROOT_DIR / "emotion_sphere_layout.json"))
    parser.add_argument("--output-csv", default=str(ROOT_DIR / "emotion_sphere_layout.csv"))


def add_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cases", default=str(ROOT_DIR / "evaluation" / "retrieval_cases.json"))
    parser.add_argument("--results-file")
    parser.add_argument("--output", default=str(ROOT_DIR / "evaluation" / "reports" / "retrieval_eval_latest.json"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--backend", choices=["faiss", "qdrant"], default="faiss")


def add_manifest_args(parser: argparse.ArgumentParser, output_flag: str = "--manifest-output") -> None:
    parser.add_argument(output_flag, dest="manifest_output", default=str(ROOT_DIR / "artifact_manifest.json"))
    parser.add_argument(
        "--artifacts",
        nargs="*",
        default=[
            "bible_cuv.index",
            "bible_cuv_embeddings.npy",
            "bible_cuv_metadata.pkl",
            "bible_cuv_config.json",
            "bible_bilingual_config.json",
            "emotion_features_map.json",
            "emotion_exemplar_verse_matches.json",
            "emotion_sphere_layout.json",
            "emotion_sphere_layout.csv",
        ],
    )


def main() -> int:
    args = parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
