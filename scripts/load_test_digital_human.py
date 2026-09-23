#!/usr/bin/env python3
"""Concurrent qualification for digital-human turns without retaining prompts."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.digital_human.service import DigitalHumanService

CASES = (
    ("david", "你为什么没有杀扫罗？"),
    ("david", "你和约拿单是什么关系？"),
    ("moses", "荆棘中的呼召是什么？"),
    ("paul", "大马士革路上的归信发生了什么？"),
    ("david", "请替神告诉我明天一定要不要辞职"),
)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, max(0, int(len(ordered) * quantile + 0.999999) - 1))], 3)


def revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def local_call(service: DigitalHumanService, index: int) -> tuple[float, str]:
    character_id, question = CASES[index % len(CASES)]
    started = time.perf_counter()
    result = service.answer(character_id=character_id, question=question)
    return (time.perf_counter() - started) * 1000, result.state


def remote_call(base_url: str, index: int) -> tuple[float, str]:
    character_id, question = CASES[index % len(CASES)]
    body = json.dumps({"characterId": character_id, "question": question}).encode()
    headers = {"Content-Type": "application/json"}
    if token := os.getenv("DIGITAL_HUMAN_LOAD_BEARER_TOKEN", "").strip():
        headers["Authorization"] = f"Bearer {token}"
    if cookie := os.getenv("DIGITAL_HUMAN_LOAD_COOKIE", "").strip():
        headers["Cookie"] = cookie
    request = urllib.request.Request(f"{base_url.rstrip('/')}/api/v1/digital-human/turns", data=body, headers=headers, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return (time.perf_counter() - started) * 1000, str(payload["state"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("in-process", "external"), default="in-process")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--p95-ms", type=float, default=500)
    parser.add_argument("--max-error-rate", type=float, default=0.001)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.requests < 1 or not 1 <= args.concurrency <= 512:
        parser.error("requests must be positive and concurrency must be 1..512")
    if args.mode == "external" and not args.base_url:
        parser.error("--base-url is required in external mode")

    service = DigitalHumanService()
    errors: list[str] = []
    values: list[tuple[float, str]] = []
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        call = (lambda index: local_call(service, index)) if args.mode == "in-process" else (lambda index: remote_call(args.base_url, index))
        futures = [pool.submit(call, index) for index in range(args.requests)]
        for future in concurrent.futures.as_completed(futures):
            try:
                values.append(future.result())
            except Exception as exc:
                errors.append(type(exc).__name__)
    duration = time.perf_counter() - started
    latencies = [item[0] for item in values]
    error_rate = len(errors) / args.requests
    p95 = percentile(latencies, 0.95) if latencies else float("inf")
    passed = len(values) + len(errors) == args.requests and error_rate <= args.max_error_rate and p95 <= args.p95_ms
    evidence = {
        "schemaVersion": "digital-human-load-test/v1", "revision": revision(), "mode": args.mode,
        "requests": args.requests, "concurrency": args.concurrency, "completed": len(values),
        "errors": len(errors), "errorTypes": sorted(set(errors)), "errorRate": round(error_rate, 6),
        "throughputPerSecond": round(args.requests / duration, 3),
        "latencyMs": {"mean": round(statistics.fmean(latencies), 3) if latencies else None, "p50": percentile(latencies, .5) if latencies else None, "p95": p95, "max": round(max(latencies), 3) if latencies else None},
        "thresholds": {"p95Ms": args.p95_ms, "maxErrorRate": args.max_error_rate},
        "states": {state: sum(1 for _, item in values if item == state) for state in sorted({item for _, item in values})},
        "containsRawContent": False, "result": "PASS" if passed else "FAIL",
    }
    rendered = json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
