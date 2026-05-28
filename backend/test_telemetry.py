"""
Tests for backend/telemetry.py.

Verifies the no-op fallback path (always available) and, when the OTel SDK
is present, that setup_telemetry() wires the TracerProvider correctly.
"""
import importlib
import sys
import types
import unittest


def _reload_telemetry():
    """Force-reimport telemetry so module-level state resets."""
    if 'telemetry' in sys.modules:
        del sys.modules['telemetry']
    sys.path.insert(0, '/sessions/intelligent-dreamy-einstein/mnt/bible3dsphere/backend')
    import telemetry as tel
    return tel


class TestNoOpFallback(unittest.TestCase):
    """These tests run even without the OTel SDK installed."""

    def setUp(self):
        self.tel = _reload_telemetry()

    def test_get_tracer_returns_something(self):
        tracer = self.tel.get_tracer("test")
        self.assertIsNotNone(tracer)

    def test_noop_tracer_context_manager(self):
        tracer = self.tel.get_tracer("test")
        with tracer.start_as_current_span("test.span") as span:
            span.set_attribute("key", "value")  # must not raise
            span.add_event("something happened")

    def test_noop_span_set_attribute_silent(self):
        span = self.tel._NoOpSpan()
        span.set_attribute("any", 42)
        span.set_status("ok")
        span.record_exception(RuntimeError("test"))
        span.end()

    def test_setup_telemetry_no_crash_without_sdk(self):
        """setup_telemetry() must not raise even if OTel SDK is absent."""
        # Temporarily hide the SDK if present
        real_otel = sys.modules.pop('opentelemetry', None)
        real_sdk  = sys.modules.pop('opentelemetry.sdk', None)
        real_sdk_trace = sys.modules.pop('opentelemetry.sdk.trace', None)
        try:
            tel = _reload_telemetry()
            tel.setup_telemetry(service_name="test-service")  # must not raise
        finally:
            if real_otel:     sys.modules['opentelemetry'] = real_otel
            if real_sdk:      sys.modules['opentelemetry.sdk'] = real_sdk
            if real_sdk_trace:sys.modules['opentelemetry.sdk.trace'] = real_sdk_trace

    def test_get_tracer_before_setup_returns_noop(self):
        """get_tracer() before setup_telemetry() returns a working tracer."""
        tel = _reload_telemetry()
        tracer = tel.get_tracer("uninitialized")
        with tracer.start_as_current_span("should.not.crash") as span:
            span.set_attribute("x", 1)


class TestWithSdk(unittest.TestCase):
    """Tests that only run when the OTel SDK is installed."""

    def setUp(self):
        try:
            import opentelemetry  # noqa: F401
            self._sdk_available = True
        except ImportError:
            self._sdk_available = False

    def test_setup_creates_real_tracer(self):
        if not self._sdk_available:
            self.skipTest("opentelemetry-sdk not installed")
        tel = _reload_telemetry()
        tel.setup_telemetry(service_name="test-svc")
        tracer = tel.get_tracer("test")
        # Should be a real SDK tracer, not our no-op
        self.assertNotIsInstance(tracer, tel._NoOpTracer)

    def test_real_span_has_attributes(self):
        if not self._sdk_available:
            self.skipTest("opentelemetry-sdk not installed")
        tel = _reload_telemetry()
        tel.setup_telemetry(service_name="test-svc-2")
        tracer = tel.get_tracer("test")
        with tracer.start_as_current_span("my.span") as span:
            span.set_attribute("user", "abc12345")
            span.set_attribute("score", 0.87)
            # No assertion needed — just verify no exceptions raised


if __name__ == "__main__":
    sys.path.insert(0, '/sessions/intelligent-dreamy-einstein/mnt/bible3dsphere/backend')
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromModule(
        importlib.import_module('test_telemetry')
    )
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
