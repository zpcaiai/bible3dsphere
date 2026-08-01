"""Generate the deterministic Batch 01-12 reviewed-asset seed migration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from ai_formation.spec_registry import asset_catalog  # noqa: E402


MIGRATION = BACKEND / "migrations" / "0240_ai_formation_reviewed_asset_catalog.sql"
ROLLBACK = BACKEND / "migrations" / "rollback" / "0240_ai_formation_reviewed_asset_catalog.down.sql"


def quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def age_bands(batch_id: str) -> list[str]:
    return {
        "04": ["16_18", "adult"],
        "06": ["0_6", "7_12", "13_15", "16_18", "adult"],
        "07": ["0_6", "7_12", "adult"],
        "08": ["13_15", "16_18", "adult"],
        "10": ["7_12", "13_15", "16_18", "adult"],
        "11": ["7_12", "13_15", "16_18", "adult"],
    }.get(batch_id, ["adult"])


def required_reviews(batch_id: str) -> list[str]:
    roles = ["theology_reviewer", "pastoral_reviewer"]
    if batch_id in {"04", "07", "08", "10", "12"}:
        roles.append("child_safety_reviewer")
    if batch_id in {"04", "09", "12"}:
        roles.append("rights_reviewer")
    if batch_id in {"07", "08", "09", "10", "12"}:
        roles.append("accessibility_reviewer")
    if batch_id == "12":
        roles.append("release_reviewer")
    return roles


def generate() -> tuple[str, str]:
    header = [
        "-- Generated from backend/ai_formation/specs by generate_ai_formation_seed_migration.py.",
        "-- All assets remain human-review gated; this migration publishes nothing.",
        "",
    ]
    statements = list(header)
    ids: list[tuple[str, str]] = []
    for asset in asset_catalog():
        canonical = json.dumps(asset["data"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sha256 = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        provenance = json.dumps(
            [{"source": asset["sourcePath"], "sha256": sha256, "generated": False}],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        ages = json.dumps(age_bands(asset["batchId"]), separators=(",", ":"))
        reviews = json.dumps(required_reviews(asset["batchId"]), separators=(",", ":"))
        statements.extend([
            "INSERT INTO sunday_school_ai_formation_content",
            "    (id,batch_id,content_kind,version,content_sha256,authority_level,review_status,age_bands_json,",
            "     content_json,source_provenance_json,required_reviews_json,created_by)",
            "VALUES(",
            f"    {quote(asset['id'])},{quote(asset['batchId'])},{quote(asset['kind'])},{quote(asset['version'])},",
            f"    {quote(sha256)},'PRODUCT_DEFAULT',{quote(asset['reviewStatus'])},{quote(ages)}::jsonb,",
            f"    {quote(canonical)}::jsonb,{quote(provenance)}::jsonb,{quote(reviews)}::jsonb,'skills-bag-01-12'",
            ") ON CONFLICT (id,version) DO NOTHING;",
            "",
        ])
        ids.append((asset["id"], asset["version"]))
    rollback = [
        "-- Removes only the immutable Skill-package seed versions; learner records are untouched.",
        "DELETE FROM sunday_school_ai_formation_content WHERE created_by='skills-bag-01-12' AND (id,version) IN (",
    ]
    rollback.extend(
        f"    ({quote(content_id)},{quote(version)}){',' if index < len(ids) - 1 else ''}"
        for index, (content_id, version) in enumerate(ids)
    )
    rollback.extend([ ");", "" ])
    return "\n".join(statements), "\n".join(rollback)


def main() -> int:
    migration, rollback = generate()
    MIGRATION.write_text(migration, encoding="utf-8")
    ROLLBACK.write_text(rollback, encoding="utf-8")
    print(f"generated {MIGRATION.name} with {len(asset_catalog())} review-only assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
