#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.digital_human.assurance import build_release_certificate, load_key_map, sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Build independently reviewed Ed25519 release evidence")
    parser.add_argument("--subject", type=Path, required=True, help="review packet JSON")
    parser.add_argument("--reviews-dir", type=Path, required=True)
    parser.add_argument("--trusted-review-keys", type=Path, required=True)
    parser.add_argument("--release-private-key", type=Path, required=True)
    parser.add_argument("--release-key-id", required=True)
    parser.add_argument("--test-evidence", type=Path, required=True)
    parser.add_argument("--build-revision")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = json.loads(args.subject.read_text(encoding="utf-8"))
    if packet.get("status") != "AWAITING_INDEPENDENT_HUMAN_REVIEW":
        raise SystemExit("invalid review packet")
    review_files = sorted(args.reviews_dir.glob("*.json"))
    reviews = [json.loads(path.read_text(encoding="utf-8")) for path in review_files]
    revision = args.build_revision or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True,
    ).strip()
    certificate = build_release_certificate(
        subject=packet["subject"], reviews=reviews,
        trusted_review_keys=load_key_map(args.trusted_review_keys),
        build_revision=revision, test_evidence_sha256=sha256_file(args.test_evidence),
        private_key_pem=args.release_private_key.read_bytes(), key_id=args.release_key_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(certificate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"signed release evidence created: {args.output}")


if __name__ == "__main__":
    main()
