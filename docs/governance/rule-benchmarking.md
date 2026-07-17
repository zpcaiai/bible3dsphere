# Rule Benchmarking

Rules are benchmarked with a fixed rule version, corpus version, expected reason codes, false-positive review, replay checksum, and latency distribution. Safety recall is evaluated separately from product quality and cannot be traded away for speed or cost.

`backend/scripts/governance_load_benchmark.py` is a synthetic micro-benchmark for the deterministic scenario kernel. It records source type, iteration count, throughput, mean, p95, model calls, and side effects. It is not a database, network, concurrency, or production-capacity test.
