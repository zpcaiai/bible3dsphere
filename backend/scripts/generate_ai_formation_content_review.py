"""Generate exact-hash human review packets for all AI Formation content."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from ai_formation.content_audit import build_review_bundle, write_review_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir", type=Path,
        default=BACKEND.parent / "docs" / "ai-formation-certification",
    )
    parser.add_argument("--statement-of-faith-version")
    parser.add_argument("--rights-attestation-id")
    args = parser.parse_args()
    bundle = build_review_bundle(
        statement_of_faith_version=args.statement_of_faith_version,
        rights_attestation_id=args.rights_attestation_id,
    )
    write_review_bundle(bundle, args.output_dir)
    print(
        f"generated {bundle['contentVersionCount']} exact-hash review packets; "
        f"status={bundle['status']}; artifactSha256={bundle['artifactSha256']}"
    )
    if bundle["blockers"]:
        print("blockers=" + ",".join(bundle["blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
