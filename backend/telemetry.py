"""
telemetry.py — OpenTelemetry setup for the MVFE pipeline.

Provides a thin wrapper around the OTel SDK that gracefully degrades to a
no-op tracer when the SDK is not installed (so the app still runs in envs
that don't have the packages).

Usage:
    from telemetry import setup_telemetry, get_tracer

    # In app lifespan (once):
    setup_telemetry(service_name="bible3dsphere-backend")

    # In any module:
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span("my.operation") as span:
        span.set_attribute("user.id_prefix", user_id[:8])
        ...

Environment variables (all optional):
    OTEL_SERVICE_NAME          override service name
    OTEL_EXPORTER_OTLP_ENDPOINT  e.g. http://localhost:4317  → enables OTLP gRPC
    OTEL_TRACES_SAMPLER        "always_on" (default) | "always_off" | "traceidratio"
    OTEL_TRACES_SAMPLER_ARG    ratio for traceidratio sampler, e.g. "0.1"
    OTEL_LOG_LEVEL             "debug" → verbose SDK logs
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ── Attempt to import OTel SDK (graceful no-op if not installed) ──────────────
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    logger.info("[telemetry] opentelemetry-sdk not installed — using no-op tracer")

_provider: Optional[object] = None


def setup_telemetry(service_name: str = "bible3dsphere-backend") -> None:
    """
    Initialize the global TracerProvider.

    Exporters selected by environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT set → BatchSpanProcessor + OTLP gRPC
      - Otherwise                        → SimpleSpanProcessor + ConsoleSpanExporter
        (console export is silenced unless OTEL_CONSOLE_EXPORT=1)
    """
    global _provider

    effective_name = os.environ.get("OTEL_SERVICE_NAME", service_name)

    if not _OTEL_AVAILABLE:
        logger.info(f"[telemetry] no-op tracer for service={effective_name}")
        return

    resource = Resource(attributes={SERVICE_NAME: effective_name})
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"[telemetry] OTLP gRPC exporter → {otlp_endpoint}")
        except ImportError:
            logger.warning(
                "[telemetry] OTEL_EXPORTER_OTLP_ENDPOINT set but "
                "opentelemetry-exporter-otlp-proto-grpc not installed; "
                "falling back to console"
            )
            _add_console_exporter(provider)
    elif os.environ.get("OTEL_CONSOLE_EXPORT", "").lower() in ("1", "true", "yes"):
        _add_console_exporter(provider)
        logger.info("[telemetry] console span exporter enabled")
    else:
        # Silent no-export in prod by default (avoids log spam)
        logger.info(f"[telemetry] tracing enabled (no exporter); set "
                    "OTEL_EXPORTER_OTLP_ENDPOINT or OTEL_CONSOLE_EXPORT=1 to export")

    trace.set_tracer_provider(provider)
    _provider = provider
    logger.info(f"[telemetry] TracerProvider ready: service={effective_name}")


def _add_console_exporter(provider) -> None:
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))


def get_tracer(name: str = "mvfe"):
    """
    Return an OpenTelemetry Tracer for `name`.
    Returns a no-op tracer if the SDK is not available or setup_telemetry()
    was not called.
    """
    if not _OTEL_AVAILABLE:
        return _NoOpTracer()
    from opentelemetry import trace as _trace
    return _trace.get_tracer(name)


# ── No-op fallback ─────────────────────────────────────────────────────────────

class _NoOpSpan:
    """A span that does nothing."""
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def set_attribute(self, *_): pass
    def set_status(self, *_): pass
    def record_exception(self, *_): pass
    def add_event(self, *_): pass
    def end(self): pass


class _NoOpTracer:
    """A tracer that produces no-op spans."""
    def start_as_current_span(self, name, **_kwargs):
        return _NoOpSpan()
    def start_span(self, name, **_kwargs):
        return _NoOpSpan()
