from __future__ import annotations

import math
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class MetricEvent:
    timestamp: float
    kind: str
    state: str
    latency_ms: float
    provider: str | None = None


class DigitalHumanMetrics:
    """Bounded, PII-free process metrics suitable for an operations dashboard."""

    def __init__(self, max_events: int = 5000):
        self._events: deque[MetricEvent] = deque(maxlen=max_events)
        self._lock = threading.Lock()

    def record_turn(self, *, state: str, latency_ms: float) -> None:
        self._append(MetricEvent(time.time(), "turn", state, max(0.0, float(latency_ms))))

    def record_provider(self, *, provider: str, state: str, latency_ms: float = 0.0) -> None:
        self._append(MetricEvent(time.time(), "provider", state, max(0.0, float(latency_ms)), provider))

    def _append(self, event: MetricEvent) -> None:
        with self._lock:
            self._events.append(event)

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, math.ceil(percentile * len(ordered)) - 1))
        return round(ordered[index], 3)

    def snapshot(self, window_seconds: int = 900) -> dict[str, object]:
        window_seconds = max(60, min(int(window_seconds), 86400))
        cutoff = time.time() - window_seconds
        with self._lock:
            events = [item for item in self._events if item.timestamp >= cutoff]
        turns = [item for item in events if item.kind == "turn"]
        latencies = [item.latency_ms for item in turns]
        provider_events = [item for item in events if item.kind == "provider" and item.provider]
        states = Counter(item.state for item in turns)
        total = len(turns)
        return {
            "windowSeconds": window_seconds,
            "turns": {
                "total": total,
                "states": dict(sorted(states.items())),
                "blockedRatePct": round(states.get("BLOCKED", 0) * 100 / total, 3) if total else 0.0,
                "speechReadyRatePct": round(states.get("READY_TO_SPEAK", 0) * 100 / total, 3) if total else 0.0,
            },
            "latencyMs": {
                "p50": self._percentile(latencies, 0.50),
                "p95": self._percentile(latencies, 0.95),
                "max": round(max(latencies), 3) if latencies else 0.0,
            },
            "providers": {
                provider: {
                    "events": len(items),
                    "lastState": max(items, key=lambda item: item.timestamp).state,
                    "states": dict(sorted(Counter(item.state for item in items).items())),
                    "latencyMsP95": self._percentile([item.latency_ms for item in items], 0.95),
                }
                for provider in sorted({str(item.provider) for item in provider_events})
                if (items := [item for item in provider_events if item.provider == provider])
            },
            "retainedEvents": len(events),
            "containsRawContent": False,
        }


metrics = DigitalHumanMetrics()
