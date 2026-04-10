#!/usr/bin/env python3
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import umap

from query_emotion_verses import (
    EMBEDDING_CACHE_FILE,
    FEATURES_FILE,
    build_feature_text,
    feature_key,
    load_json,
    load_or_build_feature_embeddings,
    l2_normalize,
)

DEFAULT_OUTPUT_JSON = "emotion_sphere_layout.json"
DEFAULT_OUTPUT_CSV = "emotion_sphere_layout.csv"
DEFAULT_NEIGHBORS = 12
DEFAULT_MIN_DIST = 0.08
DEFAULT_METRIC = "cosine"

NEAR_KEYWORDS = ("fear", "afraid", "anxiety", "anxious", "worry", "terror", "panic")
OPPOSITE_KEYWORDS = ("joy", "rejoice", "glad", "delight", "hope", "peace", "comfort")


def build_relation_vectors(embeddings: np.ndarray) -> np.ndarray:
    similarity = embeddings @ embeddings.T
    return l2_normalize(similarity.astype(np.float32))


def run_umap(relation_vectors: np.ndarray, n_neighbors: int, min_dist: float, metric: str) -> np.ndarray:
    reducer = umap.UMAP(
        n_components=3,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=42,
        init="spectral",
        transform_seed=42,
    )
    coords = reducer.fit_transform(relation_vectors)
    return coords.astype(np.float32)


def project_to_sphere(coords: np.ndarray) -> np.ndarray:
    return l2_normalize(coords.astype(np.float32))


def match_keyword_features(features: list[dict], keywords: tuple[str, ...]) -> list[int]:
    matched = []
    for idx, feature in enumerate(features):
        haystack = " ".join(
            [
                str(feature.get("source_keyword", "")),
                str(feature.get("explanation", "")),
                build_feature_text(feature),
            ]
        ).lower()
        if any(keyword in haystack for keyword in keywords):
            matched.append(idx)
    return matched


def orthonormal_basis_from_vectors(primary: np.ndarray, secondary: np.ndarray) -> np.ndarray:
    e1 = primary / (np.linalg.norm(primary) + 1e-8)
    secondary_proj = secondary - np.dot(secondary, e1) * e1
    if np.linalg.norm(secondary_proj) < 1e-8:
        fallback = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        if abs(np.dot(fallback, e1)) > 0.9:
            fallback = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        secondary_proj = fallback - np.dot(fallback, e1) * e1
    e2 = secondary_proj / (np.linalg.norm(secondary_proj) + 1e-8)
    e3 = np.cross(e1, e2)
    e3 = e3 / (np.linalg.norm(e3) + 1e-8)
    return np.stack([e1, e2, e3], axis=1)


def calibrate_orientation(sphere_coords: np.ndarray, features: list[dict]) -> np.ndarray:
    fear_ids = match_keyword_features(features, NEAR_KEYWORDS)
    joy_ids = match_keyword_features(features, OPPOSITE_KEYWORDS)

    if not fear_ids or not joy_ids:
        return sphere_coords

    fear_centroid = sphere_coords[fear_ids].mean(axis=0)
    joy_centroid = sphere_coords[joy_ids].mean(axis=0)
    if np.linalg.norm(fear_centroid) < 1e-8 or np.linalg.norm(joy_centroid) < 1e-8:
        return sphere_coords

    target_primary = fear_centroid / np.linalg.norm(fear_centroid)
    target_secondary = joy_centroid - np.dot(joy_centroid, target_primary) * target_primary
    source_primary = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    source_secondary = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    source_basis = orthonormal_basis_from_vectors(source_primary, source_secondary)
    target_basis = orthonormal_basis_from_vectors(target_primary, target_secondary)
    rotation = target_basis @ source_basis.T
    rotated = sphere_coords @ rotation.T

    fear_dot = np.mean(rotated[fear_ids] @ target_primary)
    joy_dot = np.mean(rotated[joy_ids] @ target_primary)
    if joy_dot > fear_dot:
        rotated = -rotated

    return project_to_sphere(rotated)


def compute_layout(features: list[dict], embeddings: np.ndarray, n_neighbors: int, min_dist: float, metric: str) -> np.ndarray:
    relation_vectors = build_relation_vectors(embeddings)
    coords_3d = run_umap(relation_vectors, n_neighbors=n_neighbors, min_dist=min_dist, metric=metric)
    sphere_coords = project_to_sphere(coords_3d)
    sphere_coords = calibrate_orientation(sphere_coords, features)
    return sphere_coords


def build_output_rows(features: list[dict], coords: np.ndarray, embeddings: np.ndarray) -> list[dict]:
    rows = []
    similarity = embeddings @ embeddings.T
    for idx, feature in enumerate(features):
        nearest_indices = np.argsort(similarity[idx])[::-1]
        nearest_keys = []
        for neighbor_idx in nearest_indices:
            if neighbor_idx == idx:
                continue
            neighbor = features[neighbor_idx]
            nearest_keys.append(f"{neighbor.get('layer')}:{neighbor.get('feature_id')}")
            if len(nearest_keys) >= 5:
                break
        rows.append(
            {
                "feature_key": feature_key(feature),
                "feature_id": feature.get("feature_id"),
                "layer": feature.get("layer"),
                "model_id": feature.get("model_id"),
                "source_keyword": feature.get("source_keyword"),
                "explanation": feature.get("explanation"),
                "x": float(coords[idx, 0]),
                "y": float(coords[idx, 1]),
                "z": float(coords[idx, 2]),
                "nearest_neighbors": nearest_keys,
            }
        )
    return rows


def save_outputs(rows: list[dict], json_path: str, csv_path: str) -> None:
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "feature_key",
                "feature_id",
                "layer",
                "model_id",
                "source_keyword",
                "explanation",
                "x",
                "y",
                "z",
                "nearest_neighbors",
            ],
        )
        writer.writeheader()
        for row in rows:
            row_copy = dict(row)
            row_copy["nearest_neighbors"] = " | ".join(row_copy["nearest_neighbors"])
            writer.writerow(row_copy)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic 3D sphere layout for emotion features")
    parser.add_argument("--features-file", default=FEATURES_FILE)
    parser.add_argument("--cache-file", default=EMBEDDING_CACHE_FILE)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-csv", default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--n-neighbors", type=int, default=DEFAULT_NEIGHBORS)
    parser.add_argument("--min-dist", type=float, default=DEFAULT_MIN_DIST)
    parser.add_argument("--metric", default=DEFAULT_METRIC)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = load_json(args.features_file)
    features, embeddings = load_or_build_feature_embeddings(features, args.cache_file)
    coords = compute_layout(
        features,
        embeddings,
        n_neighbors=args.n_neighbors,
        min_dist=args.min_dist,
        metric=args.metric,
    )
    rows = build_output_rows(features, coords, embeddings)
    save_outputs(rows, args.output_json, args.output_csv)
    print(
        json.dumps(
            {
                "count": len(rows),
                "output_json": args.output_json,
                "output_csv": args.output_csv,
                "n_neighbors": args.n_neighbors,
                "min_dist": args.min_dist,
                "metric": args.metric,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
