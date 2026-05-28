#!/usr/bin/env python3
import json
from pathlib import Path

import pandas as pd

INPUT_FILE = "emotion_exemplar_verse_matches.json"
OUTPUT_DIR = "emotion_match_reports"
TOP_K_PER_FEATURE = 3
TOP_N_GLOBAL = 200


def load_matches(input_file: str = INPUT_FILE) -> list[dict]:
    path = Path(input_file)
    if not path.exists():
        raise FileNotFoundError(f"结果文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_matches(records: list[dict]) -> pd.DataFrame:
    rows = []
    for record in records:
        base = {
            "feature_id": record.get("feature_id"),
            "model_id": record.get("model_id"),
            "layer": record.get("layer"),
            "source_keyword": record.get("source_keyword"),
            "explanation": record.get("explanation"),
            "exemplar_count": len(record.get("exemplar_texts", [])),
        }
        matches = record.get("matches", {})
        for language, items in matches.items():
            for rank, item in enumerate(items, start=1):
                rows.append(
                    {
                        **base,
                        "language": language,
                        "rank": rank,
                        "pk_id": item.get("pk_id"),
                        "book_name": item.get("book_name"),
                        "chapter": item.get("chapter"),
                        "verse": item.get("verse"),
                        "verse_ref": f"{item.get('book_name')} {item.get('chapter')}:{item.get('verse')}",
                        "raw_text": item.get("raw_text"),
                        "score": item.get("score"),
                    }
                )
    return pd.DataFrame(rows)


def export_top_feature_verse_pairs(df: pd.DataFrame, output_dir: Path) -> None:
    top_pairs = (
        df.sort_values(["language", "feature_id", "score"], ascending=[True, True, False])
        .groupby(["language", "feature_id"], as_index=False)
        .head(TOP_K_PER_FEATURE)
        .sort_values(["language", "feature_id", "rank", "score"], ascending=[True, True, True, False])
    )
    top_pairs.to_csv(output_dir / "top_feature_verse_pairs.csv", index=False, encoding="utf-8-sig")


def export_readable_flat_csv(df: pd.DataFrame, output_dir: Path) -> None:
    readable = df[[
        "language",
        "feature_id",
        "layer",
        "source_keyword",
        "explanation",
        "rank",
        "pk_id",
        "verse_ref",
        "score",
        "raw_text",
    ]].sort_values(["language", "feature_id", "rank"])
    readable.to_csv(output_dir / "emotion_feature_matches_readable.csv", index=False, encoding="utf-8-sig")


def export_global_top_matches(df: pd.DataFrame, output_dir: Path) -> None:
    global_top = df.sort_values("score", ascending=False).head(TOP_N_GLOBAL)
    global_top.to_csv(output_dir / "global_top_matches.csv", index=False, encoding="utf-8-sig")


def analyze_by_feature(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["language", "feature_id", "layer", "source_keyword", "explanation"], dropna=False)
        .agg(
            match_count=("pk_id", "count"),
            unique_verse_count=("pk_id", "nunique"),
            avg_score=("score", "mean"),
            max_score=("score", "max"),
            top_verse_ref=("verse_ref", "first"),
        )
        .reset_index()
        .sort_values(["language", "avg_score", "max_score"], ascending=[True, False, False])
    )


def analyze_by_book(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["language", "book_name"], dropna=False)
        .agg(
            hit_count=("pk_id", "count"),
            unique_feature_count=("feature_id", "nunique"),
            avg_score=("score", "mean"),
            max_score=("score", "max"),
        )
        .reset_index()
        .sort_values(["language", "hit_count", "avg_score"], ascending=[True, False, False])
    )


def analyze_by_language(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["language"], dropna=False)
        .agg(
            hit_count=("pk_id", "count"),
            unique_feature_count=("feature_id", "nunique"),
            unique_book_count=("book_name", "nunique"),
            avg_score=("score", "mean"),
            max_score=("score", "max"),
        )
        .reset_index()
        .sort_values("language")
    )


def export_analysis(df: pd.DataFrame, output_dir: Path) -> None:
    by_feature = analyze_by_feature(df)
    by_book = analyze_by_book(df)
    by_language = analyze_by_language(df)

    by_feature.to_csv(output_dir / "analysis_by_feature.csv", index=False, encoding="utf-8-sig")
    by_book.to_csv(output_dir / "analysis_by_book.csv", index=False, encoding="utf-8-sig")
    by_language.to_csv(output_dir / "analysis_by_language.csv", index=False, encoding="utf-8-sig")

    summary = {
        "total_rows": int(len(df)),
        "total_features": int(df["feature_id"].nunique()),
        "languages": sorted(df["language"].dropna().unique().tolist()),
        "top_books_by_language": {},
    }
    for language in sorted(df["language"].dropna().unique().tolist()):
        top_books = (
            by_book[by_book["language"] == language]
            .head(10)[["book_name", "hit_count", "avg_score", "max_score"]]
            .to_dict(orient="records")
        )
        summary["top_books_by_language"][language] = top_books

    with open(output_dir / "analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def build_reports(input_file: str = INPUT_FILE, output_dir: str = OUTPUT_DIR) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    records = load_matches(input_file)
    df = flatten_matches(records)
    if df.empty:
        raise ValueError("没有可导出的匹配结果")

    export_top_feature_verse_pairs(df, output_path)
    export_readable_flat_csv(df, output_path)
    export_global_top_matches(df, output_path)
    export_analysis(df, output_path)

    print(f"完成，报告已导出到: {output_path}")


if __name__ == "__main__":
    build_reports()
