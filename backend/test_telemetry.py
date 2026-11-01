"""
Tests for backend/telemetry.py.

Verifies the no-op fallback path (always available) and, when the OTel SDK
is present, that setup_telemetry() wires the TracerProvider correctly.
"""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

BACKEND_DIR = Path(__file__).resolve().parent


def _reload_telemetry():
    """Force-reimport telemetry so module-level state resets."""
    if 'telemetry' in sys.modules:
        del sys.modules['telemetry']
    sys.path.insert(0, str(BACKEND_DIR))
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
            from opentelemetry.sdk.trace import TracerProvider
            self._sdk_available = True
        except ImportError:
            self._sdk_available = False

    def _probe_real_sdk(self):
        """A fresh OS process avoids sharing OTel's write-once global provider."""
        script = textwrap.dedent('''
            import importlib.metadata
            import json
            import os
            import telemetry
            from opentelemetry import trace
            from opentelemetry.sdk.trace import Tracer, TracerProvider
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor
            from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

            telemetry.setup_telemetry(service_name="test-sdk-service")
            provider = trace.get_tracer_provider()
            assert isinstance(provider, TracerProvider)
            exporter = InMemorySpanExporter()
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            tracer = telemetry.get_tracer("test")
            assert isinstance(tracer, Tracer)
            assert not isinstance(tracer, telemetry._NoOpTracer)
            with tracer.start_as_current_span("my.span") as span:
                recording = span.is_recording()
                valid = span.get_span_context().is_valid
                span.set_attribute("user", "abc12345")
                span.set_attribute("score", 0.87)
            spans = exporter.get_finished_spans()
            assert len(spans) == 1
            finished = spans[0]
            print(json.dumps({
                "pid": os.getpid(),
                "sdk": importlib.metadata.version("opentelemetry-sdk"),
                "recording": recording,
                "valid": valid,
                "name": finished.name,
                "attributes": dict(finished.attributes),
                "service": finished.resource.attributes["service.name"],
            }))
            provider.shutdown()
        ''')
        env = {k: v for k, v in os.environ.items() if not k.startswith('OTEL_')}
        env['PYTHONPATH'] = str(BACKEND_DIR)
        result = subprocess.run(
            [sys.executable, '-B', '-c', script], env=env,
            capture_output=True, text=True, timeout=5, check=True,
        )
        probe = json.loads(result.stdout)
        self.assertGreater(probe['pid'], 0)
        self.assertNotEqual(probe['pid'], os.getpid())
        print(json.dumps({'real_sdk_probe': probe}))
        return probe

    def test_setup_creates_real_tracer(self):
        if not self._sdk_available:
            self.skipTest("opentelemetry-sdk not installed")
        probe = self._probe_real_sdk()
        self.assertTrue(probe['recording'])
        self.assertTrue(probe['valid'])
        self.assertEqual(probe['service'], 'test-sdk-service')

    def test_real_span_has_attributes(self):
        if not self._sdk_available:
            self.skipTest("opentelemetry-sdk not installed")
        probe = self._probe_real_sdk()
        self.assertEqual(probe['name'], 'my.span')
        self.assertEqual(probe['attributes'], {'user': 'abc12345', 'score': 0.87})


if __name__ == "__main__":
    sys.path.insert(0, str(BACKEND_DIR))
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromModule(
        importlib.import_module('test_telemetry')
    )
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
