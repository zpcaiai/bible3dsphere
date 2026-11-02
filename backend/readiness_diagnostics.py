"""Health-only request/DB timing. Never logs queries, credentials or error text."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import logging
import os
import threading
import time
from urllib.parse import urlsplit
import uuid

_current = ContextVar('readiness_trace', default=None)
_logger = logging.getLogger('readiness')
_PATHS = frozenset(('/health/live', '/health/ready', '/api/health/db'))


class RequestTrace:
    def __init__(self, request_id):
        self.request_id = request_id
        self.status = None

    def emit(self, phase, event, **fields):
        _logger.info(json.dumps({
            'kind': 'readiness_stage', 'request_id': self.request_id,
            'phase': phase, 'event': event, 'pid': os.getpid(),
            'thread_id': threading.get_ident(), 'epoch_ns': time.time_ns(),
            'monotonic_ns': time.monotonic_ns(), **fields,
        }, sort_keys=True))


@contextmanager
def request_trace(path, supplied_id, database_url):
    if path not in _PATHS:
        yield None
        return
    try:
        request_id = str(uuid.UUID(supplied_id)) if isinstance(supplied_id, str) and len(supplied_id) == 36 else str(uuid.uuid4())
    except ValueError:
        request_id = str(uuid.uuid4())
    trace = RequestTrace(request_id)
    token = _current.set(trace)
    started = time.monotonic_ns()
    # Only a hostname digest is retained, never the DSN, user, password or DB name.
    try:
        host = urlsplit(database_url or '').hostname or ''
    except ValueError:
        host = ''
    trace.emit('request', 'start', path=path, endpoint_sha256=hashlib.sha256(host.encode()).hexdigest(), load1=os.getloadavg()[0])
    try:
        yield trace
    except BaseException as exc:
        trace.emit('request', 'error', error_type=type(exc).__name__, elapsed_ms=(time.monotonic_ns() - started) / 1e6)
        raise
    else:
        trace.emit('request', 'end', status=trace.status, elapsed_ms=(time.monotonic_ns() - started) / 1e6)
    finally:
        _current.reset(token)


@contextmanager
def stage(phase):
    trace = _current.get()
    if trace is None:
        yield
        return
    start = time.monotonic_ns()
    trace.emit(phase, 'start')
    try:
        yield
    except BaseException as exc:
        trace.emit(phase, 'error', error_type=type(exc).__name__, elapsed_ms=(time.monotonic_ns() - start) / 1e6)
        raise
    else:
        trace.emit(phase, 'end', elapsed_ms=(time.monotonic_ns() - start) / 1e6)
