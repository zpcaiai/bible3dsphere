#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.digital_human.assurance import REQUIRED_REVIEW_ROLES, canonical_json
from backend.digital_human.registry import CATALOG_SHA256, CONTENT_SHA256, CONTENT_VERSION
import hashlib


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a non-approving packet for independent human review")
    parser.add_argument("--asset-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assets = json.loads(args.asset_manifest.read_text(encoding="utf-8")) if args.asset_manifest else {}
    subject = {
        "contentVersion": CONTENT_VERSION,
        "contentSha256": CONTENT_SHA256,
        "catalogSha256": CATALOG_SHA256,
        "assetManifestSha256": hashlib.sha256(canonical_json(assets)).hexdigest(),
    }
    packet = {
        "schemaVersion": "digital-human-review-packet/v1",
        "status": "AWAITING_INDEPENDENT_HUMAN_REVIEW",
        "subject": subject,
        "requiredRoles": list(REQUIRED_REVIEW_ROLES),
        "reviewQuestions": [
            "Does every claim preserve the distinction between explicit Scripture, inference and product default?",
            "Does the persona avoid fabricated revelation, spiritual authority and historical certainty?",
            "Are child, youth, crisis, privacy and secret-companion boundaries intact?",
            "Are image, model, voice, translation and source rights documented?",
            "Can users perceive disclosure, fallback and evidence in accessible modes?",
        ],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "note": "This packet is not an approval. Each role must sign its own detached attestation.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"review packet created: {args.output}")


if __name__ == "__main__":
    main()
